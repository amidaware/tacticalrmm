import mock

from tacticalrmm.test import BaseTestCase

from .serializers import AgentSerializer
from winupdate.serializers import WinUpdatePolicySerializer
from .models import Agent
from winupdate.models import WinUpdatePolicy


class TestAgentViews(BaseTestCase):
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

    @mock.patch("subprocess.run")
    def test_meshcentral_tabs(self, mock_run):
        mock_run.return_value.stdout = b"h56Ju2aThD$!wy$AcDSAz@$NnvgGa0=\n"
        url = f"/agents/{self.agent.pk}/meshtabs/"

        r = self.client.get(url)

        self.assertIn("hide=31", r.data["fileurl"])
        self.assertIn("@$NnvgGa0=", r.data["fileurl"])
        self.assertIn("/?viewmode=13", r.data["fileurl"])
        self.assertIsInstance(r.data["fileurl"], str)

        self.assertIn("hide=31", r.data["terminalurl"])
        self.assertIn("@$NnvgGa0=", r.data["terminalurl"])
        self.assertIn("/?viewmode=12", r.data["terminalurl"])
        self.assertIsInstance(r.data["terminalurl"], str)

        self.assertEqual("DESKTOP-TEST123", r.data["hostname"])

        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    @mock.patch("subprocess.run")
    def test_take_control(self, mock_run):
        mock_run.return_value.stdout = b"h56Ju2aThD$!wy$AcDSAz@$NnvgGa0=\n"
        url = f"/agents/{self.agent.pk}/takecontrol/"

        r = self.client.get(url)
        self.assertIn("hide=31", r.data)
        self.assertIn("@$NnvgGa0=", r.data)
        self.assertIn("/?viewmode=11", r.data)
        self.assertIsInstance(r.data, str)
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
