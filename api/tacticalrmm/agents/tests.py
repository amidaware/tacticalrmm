import json
import os
from unittest.mock import patch

from model_bakery import baker
from itertools import cycle

from django.conf import settings
from django.utils import timezone as djangotime
from rest_framework.authtoken.models import Token

from accounts.models import User
from tacticalrmm.test import TacticalTestCase
from .serializers import AgentSerializer
from winupdate.serializers import WinUpdatePolicySerializer
from .models import Agent
from .tasks import (
    auto_self_agent_update_task,
    update_salt_minion_task,
    get_wmi_detail_task,
    sync_salt_modules_task,
    batch_sync_modules_task,
    batch_sysinfo_task,
    OLD_64_PY_AGENT,
    OLD_32_PY_AGENT,
)
from winupdate.models import WinUpdatePolicy


class TestAgentViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

        client = baker.make("clients.Client", name="Google")
        site = baker.make("clients.Site", client=client, name="LA Office")
        self.agent = baker.make_recipe("agents.online_agent", site=site)
        baker.make_recipe("winupdate.winupdate_policy", agent=self.agent)

    def test_get_patch_policy(self):
        # make sure get_patch_policy doesn't error out when agent has policy with
        # an empty patch policy
        policy = baker.make("automation.Policy")
        self.agent.policy = policy
        self.agent.save(update_fields=["policy"])
        _ = self.agent.get_patch_policy()

        self.agent.monitoring_type = "workstation"
        self.agent.save(update_fields=["monitoring_type"])
        _ = self.agent.get_patch_policy()

        self.agent.policy = None
        self.agent.save(update_fields=["policy"])

        self.coresettings.server_policy = policy
        self.coresettings.workstation_policy = policy
        self.coresettings.save(update_fields=["server_policy", "workstation_policy"])
        _ = self.agent.get_patch_policy()

        self.agent.monitoring_type = "server"
        self.agent.save(update_fields=["monitoring_type"])
        _ = self.agent.get_patch_policy()

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

    @patch("agents.tasks.uninstall_agent_task.delay")
    def test_uninstall_catch_no_user(self, mock_task):
        # setup data
        agent_user = User.objects.create_user(
            username=self.agent.agent_id, password=User.objects.make_random_password(60)
        )
        agent_token = Token.objects.create(user=agent_user)

        url = "/agents/uninstall/"
        data = {"pk": self.agent.pk}

        agent_user.delete()

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

        site = baker.make("clients.Site")
        data = {
            "client": site.client.id,
            "site": site.id,
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
        # setup data
        site = baker.make("clients.Site", name="Ny Office")

        url = "/agents/editagent/"

        edit = {
            "id": self.agent.pk,
            "site": site.id,
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
        self.assertEqual(data["site"], site.id)

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
        self.assertEqual(self.agent.client.name, r.data["client"])
        self.assertEqual(self.agent.site.name, r.data["site"])

        self.assertEqual(r.status_code, 200)

        mock_token.return_value = "err"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("get", url)

    def test_by_client(self):
        url = f"/agents/byclient/{self.agent.client.id}/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data)

        url = f"/agents/byclient/500/"
        r = self.client.get(url)
        self.assertFalse(r.data)  # returns empty list

        self.check_not_authenticated("get", url)

    def test_by_site(self):
        url = f"/agents/bysite/{self.agent.site.id}/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data)

        url = f"/agents/bysite/500/"
        r = self.client.get(url)
        self.assertEqual(r.data, [])

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
            "client": self.agent.client.id,
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
            "client": self.agent.client.id,
            "site": self.agent.site.id,
            "agentPKs": [
                self.agent.pk,
            ],
            "cmd": "gpupdate /force",
            "timeout": 300,
            "shell": "cmd",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        mock_ret.return_value = "timeout"
        payload["client"] = self.agent.client.id
        payload["site"] = self.agent.site.id
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
            "client": self.agent.client.id,
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

        # setup data
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.agent", site=site)

        # Test client toggle maintenance mode
        data = {"type": "Client", "id": site.client.id, "action": True}

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


class TestAgentTasks(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("agents.models.Agent.salt_api_async", return_value=None)
    def test_get_wmi_detail_task(self, salt_api_async):
        self.agent = baker.make_recipe("agents.agent")
        ret = get_wmi_detail_task.s(self.agent.pk).apply()
        salt_api_async.assert_called_with(timeout=30, func="win_agent.local_sys_info")
        self.assertEqual(ret.status, "SUCCESS")

    @patch("agents.models.Agent.salt_api_cmd")
    def test_sync_salt_modules_task(self, salt_api_cmd):
        self.agent = baker.make_recipe("agents.agent")
        salt_api_cmd.return_value = {"return": [{f"{self.agent.salt_id}": []}]}
        ret = sync_salt_modules_task.s(self.agent.pk).apply()
        salt_api_cmd.assert_called_with(timeout=35, func="saltutil.sync_modules")
        self.assertEqual(
            ret.result, f"Successfully synced salt modules on {self.agent.hostname}"
        )
        self.assertEqual(ret.status, "SUCCESS")

        salt_api_cmd.return_value = "timeout"
        ret = sync_salt_modules_task.s(self.agent.pk).apply()
        self.assertEqual(ret.result, f"Unable to sync modules {self.agent.salt_id}")

        salt_api_cmd.return_value = "error"
        ret = sync_salt_modules_task.s(self.agent.pk).apply()
        self.assertEqual(ret.result, f"Unable to sync modules {self.agent.salt_id}")

    @patch("agents.models.Agent.salt_batch_async", return_value=None)
    @patch("agents.tasks.sleep", return_value=None)
    def test_batch_sync_modules_task(self, mock_sleep, salt_batch_async):
        # chunks of 50, 60 online should run only 2 times
        baker.make_recipe(
            "agents.online_agent", last_seen=djangotime.now(), _quantity=60
        )
        baker.make_recipe(
            "agents.overdue_agent",
            last_seen=djangotime.now() - djangotime.timedelta(minutes=9),
            _quantity=115,
        )
        ret = batch_sync_modules_task.s().apply()
        self.assertEqual(salt_batch_async.call_count, 2)
        self.assertEqual(ret.status, "SUCCESS")

    @patch("agents.models.Agent.salt_batch_async", return_value=None)
    @patch("agents.tasks.sleep", return_value=None)
    def test_batch_sysinfo_task(self, mock_sleep, salt_batch_async):
        # chunks of 30, 70 online should run only 3 times
        self.online = baker.make_recipe(
            "agents.online_agent", version=settings.LATEST_AGENT_VER, _quantity=70
        )
        self.overdue = baker.make_recipe(
            "agents.overdue_agent", version=settings.LATEST_AGENT_VER, _quantity=115
        )
        ret = batch_sysinfo_task.s().apply()
        self.assertEqual(salt_batch_async.call_count, 3)
        self.assertEqual(ret.status, "SUCCESS")
        salt_batch_async.reset_mock()
        [i.delete() for i in self.online]
        [i.delete() for i in self.overdue]

        # test old agents, should not run
        self.online_old = baker.make_recipe(
            "agents.online_agent", version="0.10.2", _quantity=70
        )
        self.overdue_old = baker.make_recipe(
            "agents.overdue_agent", version="0.10.2", _quantity=115
        )
        ret = batch_sysinfo_task.s().apply()
        salt_batch_async.assert_not_called()
        self.assertEqual(ret.status, "SUCCESS")

    @patch("agents.models.Agent.salt_api_async", return_value=None)
    @patch("agents.tasks.sleep", return_value=None)
    def test_update_salt_minion_task(self, mock_sleep, salt_api_async):
        # test agents that need salt update
        self.agents = baker.make_recipe(
            "agents.agent",
            version=settings.LATEST_AGENT_VER,
            salt_ver="1.0.3",
            _quantity=53,
        )
        ret = update_salt_minion_task.s().apply()
        self.assertEqual(salt_api_async.call_count, 53)
        self.assertEqual(ret.status, "SUCCESS")
        [i.delete() for i in self.agents]
        salt_api_async.reset_mock()

        # test agents that need salt update but agent version too low
        self.agents = baker.make_recipe(
            "agents.agent",
            version="0.10.2",
            salt_ver="1.0.3",
            _quantity=53,
        )
        ret = update_salt_minion_task.s().apply()
        self.assertEqual(ret.status, "SUCCESS")
        salt_api_async.assert_not_called()
        [i.delete() for i in self.agents]
        salt_api_async.reset_mock()

        # test agents already on latest salt ver
        self.agents = baker.make_recipe(
            "agents.agent",
            version=settings.LATEST_AGENT_VER,
            salt_ver=settings.LATEST_SALT_VER,
            _quantity=53,
        )
        ret = update_salt_minion_task.s().apply()
        self.assertEqual(ret.status, "SUCCESS")
        salt_api_async.assert_not_called()

    @patch("agents.models.Agent.salt_api_async")
    @patch("agents.tasks.sleep", return_value=None)
    def test_auto_self_agent_update_task(self, mock_sleep, salt_api_async):
        # test 64bit golang agent
        self.agent64 = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="1.0.0",
        )
        salt_api_async.return_value = True
        ret = auto_self_agent_update_task.s().apply()
        salt_api_async.assert_called_with(
            func="win_agent.do_agent_update_v2",
            kwargs={
                "inno": f"winagent-v{settings.LATEST_AGENT_VER}.exe",
                "url": settings.DL_64,
            },
        )
        self.assertEqual(ret.status, "SUCCESS")
        self.agent64.delete()
        salt_api_async.reset_mock()

        # test 32bit golang agent
        self.agent32 = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 7 Professional, 32 bit (build 7601.24544)",
            version="1.0.0",
        )
        salt_api_async.return_value = True
        ret = auto_self_agent_update_task.s().apply()
        salt_api_async.assert_called_with(
            func="win_agent.do_agent_update_v2",
            kwargs={
                "inno": f"winagent-v{settings.LATEST_AGENT_VER}-x86.exe",
                "url": settings.DL_32,
            },
        )
        self.assertEqual(ret.status, "SUCCESS")
        self.agent32.delete()
        salt_api_async.reset_mock()

        # test agent that has a null os field
        self.agentNone = baker.make_recipe(
            "agents.agent",
            operating_system=None,
            version="1.0.0",
        )
        ret = auto_self_agent_update_task.s().apply()
        salt_api_async.assert_not_called()
        self.agentNone.delete()
        salt_api_async.reset_mock()

        # test auto update disabled in global settings
        self.agent64 = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="1.0.0",
        )
        self.coresettings.agent_auto_update = False
        self.coresettings.save(update_fields=["agent_auto_update"])
        ret = auto_self_agent_update_task.s().apply()
        salt_api_async.assert_not_called()

        # reset core settings
        self.agent64.delete()
        salt_api_async.reset_mock()
        self.coresettings.agent_auto_update = True
        self.coresettings.save(update_fields=["agent_auto_update"])

        # test 64bit python agent
        self.agent64py = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="0.11.1",
        )
        salt_api_async.return_value = True
        ret = auto_self_agent_update_task.s().apply()
        salt_api_async.assert_called_with(
            func="win_agent.do_agent_update_v2",
            kwargs={
                "inno": "winagent-v0.11.2.exe",
                "url": OLD_64_PY_AGENT,
            },
        )
        self.assertEqual(ret.status, "SUCCESS")
        self.agent64py.delete()
        salt_api_async.reset_mock()

        # test 32bit python agent
        self.agent32py = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 7 Professional, 32 bit (build 7601.24544)",
            version="0.11.1",
        )
        salt_api_async.return_value = True
        ret = auto_self_agent_update_task.s().apply()
        salt_api_async.assert_called_with(
            func="win_agent.do_agent_update_v2",
            kwargs={
                "inno": "winagent-v0.11.2-x86.exe",
                "url": OLD_32_PY_AGENT,
            },
        )
        self.assertEqual(ret.status, "SUCCESS")