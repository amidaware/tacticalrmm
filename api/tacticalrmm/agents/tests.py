import json
import os
from unittest.mock import patch

from model_bakery import baker
from itertools import cycle

from django.conf import settings

from tacticalrmm.test import BaseTestCase, TacticalTestCase
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

        mock_ret.return_value = "error"
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

        mock_ret.return_value = "error"
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

        mock_ret.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = "error"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_power_action(self, mock_ret):
        url = f"/agents/poweraction/"

        data = {"pk": self.agent.pk, "action": "rebootnow"}
        mock_ret.return_value = True
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        mock_ret.return_value = "error"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = False
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_send_raw_cmd(self, mock_ret):
        url = f"/agents/sendrawcmd/"

        data = {
            "pk": self.agent.pk,
            "cmd": "ipconfig",
            "shell": "cmd",
            "timeout": 30,
        }
        mock_ret.return_value = "nt authority\system"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.data, str)

        mock_ret.return_value = "timeout"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = False
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_reboot_later(self, mock_ret):
        url = f"/agents/rebootlater/"

        data = {
            "pk": self.agent.pk,
            "datetime": "2025-08-29 18:41",
        }

        mock_ret.return_value = True
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["time"], "August 29, 2025 at 06:41 PM")
        self.assertEqual(r.data["agent"], self.agent.hostname)

        mock_ret.return_value = "failed"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = "timeout"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = False
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        data_invalid = {
            "pk": self.agent.pk,
            "datetime": "rm -rf /",
        }
        r = self.client.post(url, data_invalid, format="json")

        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, "Invalid date")

        self.check_not_authenticated("post", url)

    @patch("os.path.exists")
    @patch("subprocess.run")
    def test_install_agent(self, mock_subprocess, mock_file_exists):
        url = f"/agents/installagent/"

        data = {
            "client": "Google",
            "site": "LA Office",
            "arch": "64",
            "expires": 23,
            "installMethod": "exe",
            "api": "https://api.example.com",
            "agenttype": "server",
            "rdp": 1,
            "ping": 0,
            "power": 0,
        }

        mock_file_exists.return_value = False
        mock_subprocess.return_value.returncode = 0
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 406)

        mock_file_exists.return_value = True
        mock_subprocess.return_value.returncode = 1
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 413)

        mock_file_exists.return_value = True
        mock_subprocess.return_value.returncode = 0
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        data["arch"] = "32"
        mock_subprocess.return_value.returncode = 0
        mock_file_exists.return_value = False
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 415)

        data["installMethod"] = "manual"
        data["arch"] = "64"
        mock_subprocess.return_value.returncode = 0
        mock_file_exists.return_value = True
        r = self.client.post(url, data, format="json")
        self.assertIn("rdp", r.json()["cmd"])
        self.assertNotIn("power", r.json()["cmd"])
        self.assertNotIn("ping", r.json()["cmd"])

        data.update({"ping": 1, "power": 1})
        r = self.client.post(url, data, format="json")
        self.assertIn("power", r.json()["cmd"])
        self.assertIn("ping", r.json()["cmd"])

        self.check_not_authenticated("post", url)

    def test_recover(self):
        from agents.models import RecoveryAction

        self.agent.version = "0.11.1"
        self.agent.save(update_fields=["version"])
        url = "/agents/recover/"
        data = {"pk": self.agent.pk, "cmd": None, "mode": "mesh"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        data["mode"] = "salt"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("pending", r.json())

        RecoveryAction.objects.all().delete()
        data["mode"] = "command"
        data["cmd"] = "ipconfig /flushdns"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        RecoveryAction.objects.all().delete()
        data["cmd"] = None
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        RecoveryAction.objects.all().delete()

        self.agent.version = "0.9.4"
        self.agent.save(update_fields=["version"])
        data["mode"] = "salt"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("0.9.5", r.json())

        self.check_not_authenticated("post", url)

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

    @patch("agents.models.Agent.get_login_token")
    def test_meshcentral_tabs(self, mock_token):
        url = f"/agents/{self.agent.pk}/meshcentral/"
        mock_token.return_value = "askjh1k238uasdhk487234jadhsajksdhasd"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        # TODO
        # decode the cookie

        self.assertIn("&viewmode=13", r.data["file"])
        self.assertIn("&viewmode=12", r.data["terminal"])
        self.assertIn("&viewmode=11", r.data["control"])
        self.assertIn("mstsc.html?login=", r.data["webrdp"])

        self.assertEqual(self.agent.hostname, r.data["hostname"])

        self.assertEqual(r.status_code, 200)

        mock_token.return_value = "err"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

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
        self.assertEqual(self.agent.hostname, r.data)

        payload.update({"alertType": "email", "action": "disabled"})
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        agent = Agent.objects.get(pk=self.agent.pk)
        self.assertFalse(agent.overdue_email_alert)
        self.assertEqual(self.agent.hostname, r.data)

        payload.update({"alertType": "text", "action": "enabled"})
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        agent = Agent.objects.get(pk=self.agent.pk)
        self.assertTrue(agent.overdue_text_alert)
        self.assertEqual(self.agent.hostname, r.data)

        payload.update({"alertType": "text", "action": "disabled"})
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        agent = Agent.objects.get(pk=self.agent.pk)
        self.assertFalse(agent.overdue_text_alert)
        self.assertEqual(self.agent.hostname, r.data)

        payload.update({"alertType": "email", "action": "523423"})
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        payload.update({"alertType": "text", "action": "asdasd3434asdasd"})
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("post", url)

    def test_list_agents_no_detail(self):
        url = "/agents/listagentsnodetail/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_agent_edit_details(self):
        url = f"/agents/{self.agent.pk}/agenteditdetails/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        url = "/agents/48234982/agenteditdetails/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("get", url)

    @patch("winupdate.tasks.bulk_check_for_updates_task.delay")
    @patch("agents.models.Agent.salt_batch_async")
    def test_bulk_cmd_script(self, mock_ret, mock_update):
        url = "/agents/bulk/"

        mock_ret.return_value = "ok"

        payload = {
            "mode": "command",
            "target": "agents",
            "client": None,
            "site": None,
            "agentPKs": [
                self.agent.pk,
            ],
            "cmd": "gpupdate /force",
            "timeout": 300,
            "shell": "cmd",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload = {
            "mode": "command",
            "target": "agents",
            "client": None,
            "site": None,
            "agentPKs": [],
            "cmd": "gpupdate /force",
            "timeout": 300,
            "shell": "cmd",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        payload = {
            "mode": "command",
            "target": "client",
            "client": "Google",
            "site": None,
            "agentPKs": [
                self.agent.pk,
            ],
            "cmd": "gpupdate /force",
            "timeout": 300,
            "shell": "cmd",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload = {
            "mode": "command",
            "target": "client",
            "client": "Google",
            "site": "Main Office",
            "agentPKs": [
                self.agent.pk,
            ],
            "cmd": "gpupdate /force",
            "timeout": 300,
            "shell": "cmd",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload = {
            "mode": "command",
            "target": "site",
            "client": "A ASJDHkjASHDASD",
            "site": "asdasdasdasda",
            "agentPKs": [
                self.agent.pk,
            ],
            "cmd": "gpupdate /force",
            "timeout": 300,
            "shell": "cmd",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 404)

        mock_ret.return_value = "timeout"
        payload["client"] = "Google"
        payload["site"] = "Main Office"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        payload = {
            "mode": "scan",
            "target": "agents",
            "client": None,
            "site": None,
            "agentPKs": [
                self.agent.pk,
            ],
        }
        mock_ret.return_value = "ok"
        r = self.client.post(url, payload, format="json")
        mock_update.assert_called_once()
        self.assertEqual(r.status_code, 200)

        payload = {
            "mode": "install",
            "target": "client",
            "client": "Google",
            "site": None,
            "agentPKs": [
                self.agent.pk,
            ],
        }
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload["target"] = "all"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload["target"] = "asdasdsd"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        # TODO mock the script

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_restart_mesh(self, mock_ret):
        url = f"/agents/{self.agent.pk}/restartmesh/"

        mock_ret.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = "error"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = False
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = True
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.salt_api_cmd")
    def test_recover_mesh(self, mock_ret):
        url = f"/agents/{self.agent.pk}/recovermesh/"
        mock_ret.return_value = True
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.agent.hostname, r.data)

        mock_ret.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = "error"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        url = f"/agents/543656/recovermesh/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("get", url)


class TestAgentViewsNew(TacticalTestCase):
    def setUp(self):
        self.authenticate()

    def test_agent_counts(self):
        url = "/agents/agent_counts/"

        # create some data
        baker.make_recipe(
            "agents.online_agent",
            monitoring_type=cycle(["server", "workstation"]),
            _quantity=6,
        )
        agents = baker.make_recipe(
            "agents.overdue_agent",
            monitoring_type=cycle(["server", "workstation"]),
            _quantity=6,
        )

        # make an AgentOutage for every overdue agent
        baker.make("agents.AgentOutage", agent=cycle(agents), _quantity=6)

        # returned data should be this
        data = {
            "total_server_count": 6,
            "total_server_offline_count": 3,
            "total_workstation_count": 6,
            "total_workstation_offline_count": 3,
        }

        r = self.client.post(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, data)

        self.check_not_authenticated("post", url)

    def test_agent_maintenance_mode(self):
        url = "/agents/maintenance/"
        # create data
        client = baker.make("clients.Client", client="Default")
        site = baker.make("clients.Site", client=client, site="Site")
        agent = baker.make_recipe("agents.agent", client=client.client, site=site.site)

        # Test client toggle maintenance mode
        data = {"type": "Client", "id": client.id, "action": True}

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Agent.objects.get(pk=agent.pk).maintenance_mode)

        # Test site toggle maintenance mode
        data = {"type": "Site", "id": site.id, "action": False}

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Agent.objects.get(pk=agent.pk).maintenance_mode)

        # Test agent toggle maintenance mode
        data = {"type": "Agent", "id": agent.id, "action": True}

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Agent.objects.get(pk=agent.pk).maintenance_mode)

        # Test invalid payload
        data = {"type": "Invalid", "id": agent.id, "action": True}

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("post", url)
