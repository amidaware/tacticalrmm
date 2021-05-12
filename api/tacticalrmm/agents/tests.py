import json
import os
from itertools import cycle
from unittest.mock import patch

from django.conf import settings
from model_bakery import baker
from packaging import version as pyver

from logs.models import PendingAction
from tacticalrmm.test import TacticalTestCase
from winupdate.models import WinUpdatePolicy
from winupdate.serializers import WinUpdatePolicySerializer

from .models import Agent, AgentCustomField
from .serializers import AgentSerializer
from .tasks import auto_self_agent_update_task


class TestAgentsList(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_agents_list(self):
        url = "/agents/listagents/"

        # 36 total agents
        company1 = baker.make("clients.Client")
        company2 = baker.make("clients.Client")
        site1 = baker.make("clients.Site", client=company1)
        site2 = baker.make("clients.Site", client=company1)
        site3 = baker.make("clients.Site", client=company2)

        baker.make_recipe(
            "agents.online_agent", site=site1, monitoring_type="server", _quantity=15
        )
        baker.make_recipe(
            "agents.online_agent",
            site=site2,
            monitoring_type="workstation",
            _quantity=10,
        )
        baker.make_recipe(
            "agents.online_agent",
            site=site3,
            monitoring_type="server",
            _quantity=4,
        )
        baker.make_recipe(
            "agents.online_agent",
            site=site3,
            monitoring_type="workstation",
            _quantity=7,
        )

        # test all agents
        r = self.client.patch(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 36)  # type: ignore

        # test client1
        data = {"clientPK": company1.pk}  # type: ignore
        r = self.client.patch(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 25)  # type: ignore

        # test site3
        data = {"sitePK": site3.pk}  # type: ignore
        r = self.client.patch(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 11)  # type: ignore

        self.check_not_authenticated("patch", url)


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
        baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version=settings.LATEST_AGENT_VER,
            _quantity=15,
        )
        baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="1.3.0",
            _quantity=15,
        )

        pks: list[int] = list(
            Agent.objects.only("pk", "version").values_list("pk", flat=True)
        )

        data = {"pks": pks}
        expected: list[int] = [
            i.pk
            for i in Agent.objects.only("pk", "version")
            if pyver.parse(i.version) < pyver.parse(settings.LATEST_AGENT_VER)
        ]

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        mock_task.assert_called_with(pks=expected)

        self.check_not_authenticated("post", url)

    @patch("time.sleep")
    @patch("agents.models.Agent.nats_cmd")
    def test_ping(self, nats_cmd, mock_sleep):
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
    def test_get_event_log(self, nats_cmd):
        url = f"/agents/{self.agent.pk}/geteventlog/Application/22/"

        with open(
            os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/appeventlog.json")
        ) as f:
            nats_cmd.return_value = json.load(f)

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_with(
            {
                "func": "eventlog",
                "timeout": 30,
                "payload": {
                    "logname": "Application",
                    "days": str(22),
                },
            },
            timeout=32,
        )

        url = f"/agents/{self.agent.pk}/geteventlog/Security/6/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_with(
            {
                "func": "eventlog",
                "timeout": 180,
                "payload": {
                    "logname": "Security",
                    "days": str(6),
                },
            },
            timeout=182,
        )

        nats_cmd.return_value = "timeout"
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
        self.assertIsInstance(r.data, str)  # type: ignore

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
        self.assertEqual(r.data["time"], "August 29, 2025 at 06:41 PM")  # type: ignore
        self.assertEqual(r.data["agent"], self.agent.hostname)  # type: ignore

        nats_data = {
            "func": "schedtask",
            "schedtaskpayload": {
                "type": "schedreboot",
                "deleteafter": True,
                "trigger": "once",
                "name": r.data["task_name"],  # type: ignore
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
        self.assertEqual(r.data, "Invalid date")  # type: ignore

        self.check_not_authenticated("patch", url)

    @patch("os.path.exists")
    def test_install_agent(self, mock_file_exists):
        url = "/agents/installagent/"

        site = baker.make("clients.Site")
        data = {
            "client": site.client.id,  # type: ignore
            "site": site.id,  # type: ignore
            "arch": "64",
            "expires": 23,
            "installMethod": "manual",
            "api": "https://api.example.com",
            "agenttype": "server",
            "rdp": 1,
            "ping": 0,
            "power": 0,
            "fileName": "rmm-client-site-server.exe",
        }

        mock_file_exists.return_value = False
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 406)

        mock_file_exists.return_value = True
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)

        data["arch"] = "32"
        mock_file_exists.return_value = False
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 415)

        data["arch"] = "64"
        mock_file_exists.return_value = True
        r = self.client.post(url, data, format="json")
        self.assertIn("rdp", r.json()["cmd"])
        self.assertNotIn("power", r.json()["cmd"])

        data.update({"ping": 1, "power": 1})
        r = self.client.post(url, data, format="json")
        self.assertIn("power", r.json()["cmd"])
        self.assertIn("ping", r.json()["cmd"])

        data["installMethod"] = "powershell"
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_recover(self, nats_cmd):
        from agents.models import RecoveryAction

        RecoveryAction.objects.all().delete()
        url = "/agents/recover/"
        agent = baker.make_recipe("agents.online_agent")

        # test mesh realtime
        data = {"pk": agent.pk, "cmd": None, "mode": "mesh"}
        nats_cmd.return_value = "ok"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(RecoveryAction.objects.count(), 0)
        nats_cmd.assert_called_with(
            {"func": "recover", "payload": {"mode": "mesh"}}, timeout=10
        )
        nats_cmd.reset_mock()

        # test mesh with agent rpc not working
        data = {"pk": agent.pk, "cmd": None, "mode": "mesh"}
        nats_cmd.return_value = "timeout"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(RecoveryAction.objects.count(), 1)
        mesh_recovery = RecoveryAction.objects.first()
        self.assertEqual(mesh_recovery.mode, "mesh")
        nats_cmd.reset_mock()
        RecoveryAction.objects.all().delete()

        # test tacagent realtime
        data = {"pk": agent.pk, "cmd": None, "mode": "tacagent"}
        nats_cmd.return_value = "ok"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(RecoveryAction.objects.count(), 0)
        nats_cmd.assert_called_with(
            {"func": "recover", "payload": {"mode": "tacagent"}}, timeout=10
        )
        nats_cmd.reset_mock()

        # test tacagent with rpc not working
        data = {"pk": agent.pk, "cmd": None, "mode": "tacagent"}
        nats_cmd.return_value = "timeout"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(RecoveryAction.objects.count(), 0)
        nats_cmd.reset_mock()

        # test shell cmd without command
        data = {"pk": agent.pk, "cmd": None, "mode": "command"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(RecoveryAction.objects.count(), 0)

        # test shell cmd
        data = {"pk": agent.pk, "cmd": "shutdown /r /t 10 /f", "mode": "command"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(RecoveryAction.objects.count(), 1)
        cmd_recovery = RecoveryAction.objects.first()
        self.assertEqual(cmd_recovery.mode, "command")
        self.assertEqual(cmd_recovery.command, "shutdown /r /t 10 /f")

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
            "site": site.id,  # type: ignore
            "monitoring_type": "workstation",
            "description": "asjdk234andasd",
            "offline_time": 4,
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
        self.assertEqual(data["site"], site.id)  # type: ignore

        policy = WinUpdatePolicy.objects.get(agent=self.agent)
        data = WinUpdatePolicySerializer(policy).data
        self.assertEqual(data["run_time_days"], [2, 3, 6])

        # test adding custom fields
        field = baker.make("core.CustomField", model="agent", type="number")
        edit = {
            "id": self.agent.pk,
            "site": site.id,  # type: ignore
            "description": "asjdk234andasd",
            "custom_fields": [{"field": field.id, "string_value": "123"}],  # type: ignore
        }

        r = self.client.patch(url, edit, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            AgentCustomField.objects.filter(agent=self.agent, field=field).exists()
        )

        # test edit custom field
        edit = {
            "id": self.agent.pk,
            "site": site.id,  # type: ignore
            "description": "asjdk234andasd",
            "custom_fields": [{"field": field.id, "string_value": "456"}],  # type: ignore
        }

        r = self.client.patch(url, edit, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            AgentCustomField.objects.get(agent=agent, field=field).value,
            "456",
        )
        self.check_not_authenticated("patch", url)

    @patch("agents.models.Agent.get_login_token")
    def test_meshcentral_tabs(self, mock_token):
        url = f"/agents/{self.agent.pk}/meshcentral/"
        mock_token.return_value = "askjh1k238uasdhk487234jadhsajksdhasd"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        # TODO
        # decode the cookie

        self.assertIn("&viewmode=13", r.data["file"])  # type: ignore
        self.assertIn("&viewmode=12", r.data["terminal"])  # type: ignore
        self.assertIn("&viewmode=11", r.data["control"])  # type: ignore

        self.assertIn("&gotonode=", r.data["file"])  # type: ignore
        self.assertIn("&gotonode=", r.data["terminal"])  # type: ignore
        self.assertIn("&gotonode=", r.data["control"])  # type: ignore

        self.assertIn("?login=", r.data["file"])  # type: ignore
        self.assertIn("?login=", r.data["terminal"])  # type: ignore
        self.assertIn("?login=", r.data["control"])  # type: ignore

        self.assertEqual(self.agent.hostname, r.data["hostname"])  # type: ignore
        self.assertEqual(self.agent.client.name, r.data["client"])  # type: ignore
        self.assertEqual(self.agent.site.name, r.data["site"])  # type: ignore

        self.assertEqual(r.status_code, 200)

        mock_token.return_value = "err"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("get", url)

    def test_overdue_action(self):
        url = "/agents/overdueaction/"

        payload = {"pk": self.agent.pk, "overdue_email_alert": True}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        agent = Agent.objects.get(pk=self.agent.pk)
        self.assertTrue(agent.overdue_email_alert)
        self.assertEqual(self.agent.hostname, r.data)  # type: ignore

        payload = {"pk": self.agent.pk, "overdue_text_alert": False}
        r = self.client.post(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        agent = Agent.objects.get(pk=self.agent.pk)
        self.assertFalse(agent.overdue_text_alert)
        self.assertEqual(self.agent.hostname, r.data)  # type: ignore

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
        self.assertIn(self.agent.hostname, r.data)  # type: ignore
        nats_cmd.assert_called_with(
            {"func": "recover", "payload": {"mode": "mesh"}}, timeout=90
        )

        nats_cmd.return_value = "timeout"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

        url = f"/agents/543656/recovermesh/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("get", url)

    @patch("agents.tasks.run_script_email_results_task.delay")
    @patch("agents.models.Agent.run_script")
    def test_run_script(self, run_script, email_task):
        run_script.return_value = "ok"
        url = "/agents/runscript/"
        script = baker.make_recipe("scripts.script")

        # test wait
        data = {
            "pk": self.agent.pk,
            "scriptPK": script.pk,
            "output": "wait",
            "args": [],
            "timeout": 15,
        }

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        run_script.assert_called_with(
            scriptpk=script.pk, args=[], timeout=18, wait=True
        )
        run_script.reset_mock()

        # test email default
        data = {
            "pk": self.agent.pk,
            "scriptPK": script.pk,
            "output": "email",
            "args": ["abc", "123"],
            "timeout": 15,
            "emailmode": "default",
            "emails": ["admin@example.com", "bob@example.com"],
        }
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        email_task.assert_called_with(
            agentpk=self.agent.pk,
            scriptpk=script.pk,
            nats_timeout=18,
            emails=[],
            args=["abc", "123"],
        )
        email_task.reset_mock()

        # test email overrides
        data["emailmode"] = "custom"
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        email_task.assert_called_with(
            agentpk=self.agent.pk,
            scriptpk=script.pk,
            nats_timeout=18,
            emails=["admin@example.com", "bob@example.com"],
            args=["abc", "123"],
        )

        # test fire and forget
        data = {
            "pk": self.agent.pk,
            "scriptPK": script.pk,
            "output": "forget",
            "args": ["hello", "world"],
            "timeout": 22,
        }

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        run_script.assert_called_with(
            scriptpk=script.pk, args=["hello", "world"], timeout=25
        )


class TestAgentViewsNew(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    """ def test_agent_counts(self):
        url = "/agents/agent_counts/"

        # create some data
        baker.make_recipe(
            "agents.online_agent",
            monitoring_type=cycle(["server", "workstation"]),
            _quantity=6,
        )
        baker.make_recipe(
            "agents.overdue_agent",
            monitoring_type=cycle(["server", "workstation"]),
            _quantity=6,
        )

        # returned data should be this
        data = {
            "total_server_count": 6,
            "total_server_offline_count": 3,
            "total_workstation_count": 6,
            "total_workstation_offline_count": 3,
        }

        r = self.client.post(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, data)  # type: ignore

        self.check_not_authenticated("post", url) """

    def test_agent_maintenance_mode(self):
        url = "/agents/maintenance/"

        # setup data
        site = baker.make("clients.Site")
        agent = baker.make_recipe("agents.agent", site=site)

        # Test client toggle maintenance mode
        data = {"type": "Client", "id": site.client.id, "action": True}  # type: ignore

        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Agent.objects.get(pk=agent.pk).maintenance_mode)

        # Test site toggle maintenance mode
        data = {"type": "Site", "id": site.id, "action": False}  # type: ignore

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

    @patch("agents.utils.get_exegen_url")
    @patch("agents.models.Agent.nats_cmd")
    def test_agent_update(self, nats_cmd, get_exe):
        from agents.tasks import agent_update

        agent_noarch = baker.make_recipe(
            "agents.agent",
            operating_system="Error getting OS",
            version=settings.LATEST_AGENT_VER,
        )
        r = agent_update(agent_noarch.pk)
        self.assertEqual(r, "noarch")

        agent_130 = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="1.3.0",
        )
        r = agent_update(agent_130.pk)
        self.assertEqual(r, "not supported")

        # test __without__ code signing
        agent64_nosign = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="1.4.14",
        )

        r = agent_update(agent64_nosign.pk, None)
        self.assertEqual(r, "created")
        action = PendingAction.objects.get(agent__pk=agent64_nosign.pk)
        self.assertEqual(action.action_type, "agentupdate")
        self.assertEqual(action.status, "pending")
        self.assertEqual(
            action.details["url"],
            f"https://github.com/wh1te909/rmmagent/releases/download/v{settings.LATEST_AGENT_VER}/winagent-v{settings.LATEST_AGENT_VER}.exe",
        )
        self.assertEqual(
            action.details["inno"], f"winagent-v{settings.LATEST_AGENT_VER}.exe"
        )
        self.assertEqual(action.details["version"], settings.LATEST_AGENT_VER)
        nats_cmd.assert_called_with(
            {
                "func": "agentupdate",
                "payload": {
                    "url": f"https://github.com/wh1te909/rmmagent/releases/download/v{settings.LATEST_AGENT_VER}/winagent-v{settings.LATEST_AGENT_VER}.exe",
                    "version": settings.LATEST_AGENT_VER,
                    "inno": f"winagent-v{settings.LATEST_AGENT_VER}.exe",
                },
            },
            wait=False,
        )

        # test __with__ code signing (64 bit)
        codesign = baker.make("core.CodeSignToken", token="testtoken123")
        agent64_sign = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="1.4.14",
        )

        nats_cmd.return_value = "ok"
        get_exe.return_value = "https://exe.tacticalrmm.io"
        r = agent_update(agent64_sign.pk, codesign.token)  # type: ignore
        self.assertEqual(r, "created")
        nats_cmd.assert_called_with(
            {
                "func": "agentupdate",
                "payload": {
                    "url": f"https://exe.tacticalrmm.io/api/v1/winagents/?version={settings.LATEST_AGENT_VER}&arch=64&token=testtoken123",  # type: ignore
                    "version": settings.LATEST_AGENT_VER,
                    "inno": f"winagent-v{settings.LATEST_AGENT_VER}.exe",
                },
            },
            wait=False,
        )
        action = PendingAction.objects.get(agent__pk=agent64_sign.pk)
        self.assertEqual(action.action_type, "agentupdate")
        self.assertEqual(action.status, "pending")

        # test __with__ code signing (32 bit)
        agent32_sign = baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 32 bit (build 19041.450)",
            version="1.4.14",
        )

        nats_cmd.return_value = "ok"
        get_exe.return_value = "https://exe.tacticalrmm.io"
        r = agent_update(agent32_sign.pk, codesign.token)  # type: ignore
        self.assertEqual(r, "created")
        nats_cmd.assert_called_with(
            {
                "func": "agentupdate",
                "payload": {
                    "url": f"https://exe.tacticalrmm.io/api/v1/winagents/?version={settings.LATEST_AGENT_VER}&arch=32&token=testtoken123",  # type: ignore
                    "version": settings.LATEST_AGENT_VER,
                    "inno": f"winagent-v{settings.LATEST_AGENT_VER}-x86.exe",
                },
            },
            wait=False,
        )
        action = PendingAction.objects.get(agent__pk=agent32_sign.pk)
        self.assertEqual(action.action_type, "agentupdate")
        self.assertEqual(action.status, "pending")

    @patch("agents.tasks.agent_update")
    @patch("agents.tasks.sleep", return_value=None)
    def test_auto_self_agent_update_task(self, mock_sleep, agent_update):
        baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version=settings.LATEST_AGENT_VER,
            _quantity=23,
        )
        baker.make_recipe(
            "agents.agent",
            operating_system="Windows 10 Pro, 64 bit (build 19041.450)",
            version="1.3.0",
            _quantity=33,
        )

        self.coresettings.agent_auto_update = False
        self.coresettings.save(update_fields=["agent_auto_update"])

        r = auto_self_agent_update_task.s().apply()
        self.assertEqual(agent_update.call_count, 0)

        self.coresettings.agent_auto_update = True
        self.coresettings.save(update_fields=["agent_auto_update"])

        r = auto_self_agent_update_task.s().apply()
        self.assertEqual(agent_update.call_count, 33)
