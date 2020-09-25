import base64
import json
import os
import zlib
from unittest.mock import patch

from django.conf import settings

from tacticalrmm.test import BaseTestCase
from .serializers import AgentSerializer
from winupdate.serializers import WinUpdatePolicySerializer
from .models import Agent
from winupdate.models import WinUpdatePolicy


class TestAgentViews(BaseTestCase):
    def test_get_agent_versions(self):
        url = "/agents/getagentversions/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        assert any(i["hostname"] == self.agent.hostname for i in r.json()["agents"])

        self.check_not_authenticated("get", url)

    @patch("agents.tasks.send_agent_update_task.delay")
    def test_update_agents(self, mock_task):
        url = "/agents/updateagents/"
        data = {"pks": [1, 2, 3, 5, 10], "version": "0.11.1"}

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        mock_task.assert_called_with(pks=data["pks"], version=data["version"])

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_ping(self, mock_ret):
        url = f"/agents/{self.agent.pk}/ping/"

        mock_ret.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        ret = {"name": self.agent.hostname, "status": "offline"}
        self.assertEqual(r.json(), ret)

        mock_ret.return_value = "error"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        ret = {"name": self.agent.hostname, "status": "offline"}
        self.assertEqual(r.json(), ret)

        mock_ret.return_value = True
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        ret = {"name": self.agent.hostname, "status": "online"}
        self.assertEqual(r.json(), ret)

        mock_ret.return_value = False
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        ret = {"name": self.agent.hostname, "status": "offline"}
        self.assertEqual(r.json(), ret)

        self.check_not_authenticated("get", url)

    @patch("agents.tasks.uninstall_agent_task.delay")
    def test_uninstall(self, mock_task):
        url = "/agents/uninstall/"
        data = {"pk": self.agent.pk}

        r = self.client.delete(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        mock_task.assert_called_with(self.agent.salt_id)

        self.check_not_authenticated("delete", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_get_processes(self, mock_ret):
        url = f"/agents/{self.agent.pk}/getprocs/"

        with open(
            os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/procs.json")
        ) as f:
            mock_ret.return_value = json.load(f)

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        assert any(i["name"] == "Registry" for i in mock_ret.return_value)
        assert any(
            i["memory_percent"] == 0.004843281375620747 for i in mock_ret.return_value
        )

        mock_ret.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_kill_proc(self, mock_ret):
        url = f"/agents/{self.agent.pk}/8234/killproc/"

        mock_ret.return_value = True
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        mock_ret.return_value = False
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_get_event_log(self, mock_ret):
        url = f"/agents/{self.agent.pk}/geteventlog/Application/30/"

        with open(
            os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/eventlograw.json")
        ) as f:
            mock_ret.return_value = json.load(f)

        with open(
            os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/appeventlog.json")
        ) as f:
            decoded = json.load(f)

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(decoded, r.json())

        self.check_not_authenticated("get", url)

    def test_agents_list(self):
        url = "/agents/listagents/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_agents_agent_detail(self):
        url = f"/agents/{self.agent.pk}/agentdetail/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_edit_agent(self):
        url = "/agents/editagent/"

        edit = {
            "id": self.agent.pk,
            "client": "Facebook",
            "site": "NY Office",
            "monitoring_type": "workstation",
            "description": "asjdk234andasd",
            "overdue_time": 300,
            "check_interval": 60,
            "overdue_email_alert": True,
            "overdue_text_alert": False,
            "winupdatepolicy": [
                {
                    "critical": "approve",
                    "important": "approve",
                    "moderate": "manual",
                    "low": "ignore",
                    "other": "ignore",
                    "run_time_hour": 5,
                    "run_time_days": [2, 3, 6],
                    "reboot_after_install": "required",
                    "reprocess_failed": True,
                    "reprocess_failed_times": 13,
                    "email_if_fail": True,
                    "agent": self.agent.pk,
                }
            ],
        }

        r = self.client.patch(url, edit, format="json")
        self.assertEqual(r.status_code, 200)

        agent = Agent.objects.get(pk=self.agent.pk)
        data = AgentSerializer(agent).data
        self.assertEqual(data["site"], "NY Office")

        policy = WinUpdatePolicy.objects.get(agent=self.agent)
        data = WinUpdatePolicySerializer(policy).data
        self.assertEqual(data["run_time_days"], [2, 3, 6])

        self.check_not_authenticated("patch", url)

    def test_meshcentral_tabs(self):
        url = f"/agents/{self.agent.pk}/meshcentral/"

        r = self.client.get(url)

        # TODO
        # decode the cookie

        self.assertIn("&viewmode=13", r.data["file"])
        self.assertIn("&viewmode=12", r.data["terminal"])
        self.assertIn("&viewmode=11", r.data["control"])
        self.assertIn("mstsc.html?login=", r.data["webrdp"])

        self.assertEqual(self.agent.hostname, r.data["hostname"])

        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_by_client(self):
        url = "/agents/byclient/Google/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data)

        url = f"/agents/byclient/Majh3 Akj34 ad/"
        r = self.client.get(url)
        self.assertFalse(r.data)  # returns empty list

        self.check_not_authenticated("get", url)

    def test_by_site(self):
        url = f"/agents/bysite/Google/Main Office/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data)

        url = f"/agents/bysite/Google/Ajdaksd Office/"
        r = self.client.get(url)
        self.assertFalse(r.data)

        self.check_not_authenticated("get", url)

    def test_overdue_action(self):
        url = "/agents/overdueaction/"

        payload = {"pk": self.agent.pk, "alertType": "email", "action": "enabled"}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        agent = Agent.objects.get(pk=self.agent.pk)
        self.assertTrue(agent.overdue_email_alert)

        self.check_not_authenticated("post", url)
