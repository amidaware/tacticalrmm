import json
import os
from unittest.mock import patch

from model_bakery import baker
from itertools import cycle

from django.test import TestCase, override_settings
from django.conf import settings
from django.utils import timezone as djangotime
from logs.models import PendingAction

from tacticalrmm.test import TacticalTestCase
from .serializers import AgentSerializer
from winupdate.serializers import WinUpdatePolicySerializer
from .models import Agent
from winupdate.models import WinUpdatePolicy


class TestAgentViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

        client = baker.make("clients.Client", name="Google")
        site = baker.make("clients.Site", client=client, name="LA Office")
        self.agent = baker.make_recipe(
            "agents.online_agent", site=site, version="1.1.1"
        )
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

    @patch("agents.models.Agent.nats_cmd")
    def test_ping(self, nats_cmd):
        url = f"/agents/{self.agent.pk}/ping/"

        nats_cmd.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        ret = {"name": self.agent.hostname, "status": "offline"}
        self.assertEqual(r.json(), ret)

        nats_cmd.return_value = "natsdown"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        ret = {"name": self.agent.hostname, "status": "offline"}
        self.assertEqual(r.json(), ret)

        nats_cmd.return_value = "pong"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        ret = {"name": self.agent.hostname, "status": "online"}
        self.assertEqual(r.json(), ret)

        nats_cmd.return_value = "asdasjdaksdasd"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        ret = {"name": self.agent.hostname, "status": "offline"}
        self.assertEqual(r.json(), ret)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    @patch("agents.views.reload_nats")
    def test_uninstall(self, reload_nats, nats_cmd):
        url = "/agents/uninstall/"
        data = {"pk": self.agent.pk}

        r = self.client.delete(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        nats_cmd.assert_called_with({"func": "uninstall"}, wait=False)
        reload_nats.assert_called_once()

        self.check_not_authenticated("delete", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_get_processes(self, mock_ret):
        agent_old = baker.make_recipe("agents.online_agent", version="1.1.12")
        url_old = f"/agents/{agent_old.pk}/getprocs/"
        r = self.client.get(url_old)
        self.assertEqual(r.status_code, 400)

        agent = baker.make_recipe("agents.online_agent", version="1.2.0")
        url = f"/agents/{agent.pk}/getprocs/"

        with open(
            os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/procs.json")
        ) as f:
            mock_ret.return_value = json.load(f)

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        assert any(i["name"] == "Registry" for i in mock_ret.return_value)
        assert any(i["membytes"] == 434655234324 for i in mock_ret.return_value)

        mock_ret.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_kill_proc(self, nats_cmd):
        url = f"/agents/{self.agent.pk}/8234/killproc/"

        nats_cmd.return_value = "ok"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        nats_cmd.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        nats_cmd.return_value = "process doesn't exist"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_get_event_log(self, mock_ret):
        url = f"/agents/{self.agent.pk}/geteventlog/Application/30/"

        with open(
            os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/appeventlog.json")
        ) as f:
            mock_ret.return_value = json.load(f)

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        mock_ret.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_reboot_now(self, nats_cmd):
        url = f"/agents/reboot/"

        data = {"pk": self.agent.pk}
        nats_cmd.return_value = "ok"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_with({"func": "rebootnow"}, timeout=10)

        nats_cmd.return_value = "timeout"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.nats_cmd")
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

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_reboot_later(self, nats_cmd):
        url = f"/agents/reboot/"

        data = {
            "pk": self.agent.pk,
            "datetime": "2025-08-29 18:41",
        }

        nats_cmd.return_value = "ok"
        r = self.client.patch(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["time"], "August 29, 2025 at 06:41 PM")
        self.assertEqual(r.data["agent"], self.agent.hostname)

        nats_data = {
            "func": "schedtask",
            "schedtaskpayload": {
                "type": "schedreboot",
                "trigger": "once",
                "name": r.data["task_name"],
                "year": 2025,
                "month": "August",
                "day": 29,
                "hour": 18,
                "min": 41,
            },
        }
        nats_cmd.assert_called_with(nats_data, timeout=10)

        nats_cmd.return_value = "error creating task"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        data_invalid = {
            "pk": self.agent.pk,
            "datetime": "rm -rf /",
        }
        r = self.client.patch(url, data_invalid, format="json")

        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, "Invalid date")

        self.check_not_authenticated("patch", url)

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

        data["mode"] = "mesh"
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
        data["mode"] = "mesh"
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

        self.assertIn("&gotonode=", r.data["file"])
        self.assertIn("&gotonode=", r.data["terminal"])
        self.assertIn("&gotonode=", r.data["control"])

        self.assertIn("?login=", r.data["file"])
        self.assertIn("?login=", r.data["terminal"])
        self.assertIn("?login=", r.data["control"])

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

        payload = {"pk": self.agent.pk, "overdue_email_alert": True}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        agent = Agent.objects.get(pk=self.agent.pk)
        self.assertTrue(agent.overdue_email_alert)
        self.assertEqual(self.agent.hostname, r.data)

        payload = {"pk": self.agent.pk, "overdue_text_alert": False}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        agent = Agent.objects.get(pk=self.agent.pk)
        self.assertFalse(agent.overdue_text_alert)
        self.assertEqual(self.agent.hostname, r.data)

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

    """ @patch("winupdate.tasks.bulk_check_for_updates_task.delay")
    @patch("scripts.tasks.handle_bulk_script_task.delay")
    @patch("scripts.tasks.handle_bulk_command_task.delay")
    @patch("agents.models.Agent.salt_batch_async")
    def test_bulk_cmd_script(
        self, salt_batch_async, bulk_command, bulk_script, mock_update
    ):
        url = "/agents/bulk/"

        payload = {
            "mode": "command",
            "monType": "all",
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
        bulk_command.assert_called_with([self.agent.pk], "gpupdate /force", "cmd", 300)
        self.assertEqual(r.status_code, 200)

        payload = {
            "mode": "command",
            "monType": "servers",
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
            "monType": "workstations",
            "target": "client",
            "client": self.agent.client.id,
            "site": None,
            "agentPKs": [],
            "cmd": "gpupdate /force",
            "timeout": 300,
            "shell": "cmd",
        }

        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        bulk_command.assert_called_with([self.agent.pk], "gpupdate /force", "cmd", 300)

        payload = {
            "mode": "command",
            "monType": "all",
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
        bulk_command.assert_called_with([self.agent.pk], "gpupdate /force", "cmd", 300)

        payload = {
            "mode": "scan",
            "monType": "all",
            "target": "agents",
            "client": None,
            "site": None,
            "agentPKs": [
                self.agent.pk,
            ],
        }
        r = self.client.post(url, payload, format="json")
        mock_update.assert_called_with(minions=[self.agent.salt_id])
        self.assertEqual(r.status_code, 200)

        payload = {
            "mode": "install",
            "monType": "all",
            "target": "client",
            "client": self.agent.client.id,
            "site": None,
            "agentPKs": [
                self.agent.pk,
            ],
        }
        salt_batch_async.return_value = "ok"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload["target"] = "all"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload["target"] = "asdasdsd"
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        # TODO mock the script

        self.check_not_authenticated("post", url) """

    @patch("agents.models.Agent.nats_cmd")
    def test_recover_mesh(self, nats_cmd):
        url = f"/agents/{self.agent.pk}/recovermesh/"
        nats_cmd.return_value = "ok"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.agent.hostname, r.data)
        nats_cmd.assert_called_with(
            {"func": "recover", "payload": {"mode": "mesh"}}, timeout=45
        )

        nats_cmd.return_value = "timeout"
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

    @patch("agents.models.Agent.nats_cmd")
    def test_agent_update(self, nats_cmd):
        from agents.tasks import agent_update

        agent_noarch = baker.make_recipe(
            "agents.agent",
            operating_system="Error getting OS",
            version="1.1.11",
        )
        r = agent_update(agent_noarch.pk)
        self.assertEqual(r, "noarch")
        self.assertEqual(
            PendingAction.objects.filter(
                agent=agent_noarch, action_type="agentupdate"
            ).count(),
            0,
        )

        agent64_111 = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="1.1.11",
        )

        r = agent_update(agent64_111.pk)
        self.assertEqual(r, "created")
        action = PendingAction.objects.get(agent__pk=agent64_111.pk)
        self.assertEqual(action.action_type, "agentupdate")
        self.assertEqual(action.status, "pending")
        self.assertEqual(
            action.details["url"],
            "https://github.com/wh1te909/rmmagent/releases/download/v1.3.0/winagent-v1.3.0.exe",
        )
        self.assertEqual(action.details["inno"], "winagent-v1.3.0.exe")
        self.assertEqual(action.details["version"], "1.3.0")

        agent_64_130 = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="1.3.0",
        )
        nats_cmd.return_value = "ok"
        r = agent_update(agent_64_130.pk)
        self.assertEqual(r, "created")
        nats_cmd.assert_called_with(
            {
                "func": "agentupdate",
                "payload": {
                    "url": settings.DL_64,
                    "version": settings.LATEST_AGENT_VER,
                    "inno": f"winagent-v{settings.LATEST_AGENT_VER}.exe",
                },
            },
            wait=False,
        )

        agent64_old = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="1.2.1",
        )
        nats_cmd.return_value = "ok"
        r = agent_update(agent64_old.pk)
        self.assertEqual(r, "created")
        nats_cmd.assert_called_with(
            {
                "func": "agentupdate",
                "payload": {
                    "url": "https://github.com/wh1te909/rmmagent/releases/download/v1.3.0/winagent-v1.3.0.exe",
                    "version": "1.3.0",
                    "inno": "winagent-v1.3.0.exe",
                },
            },
            wait=False,
        )

    """ @patch("agents.models.Agent.salt_api_async")
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
        self.assertEqual(ret.status, "SUCCESS") """
