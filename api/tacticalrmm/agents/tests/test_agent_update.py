from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from model_bakery import baker

from agents.models import Agent
from agents.tasks import auto_self_agent_update_task, send_agent_update_task
from tacticalrmm.constants import (
    AgentMonType,
    AgentPlat,
    AGENT_DEFER,
    GoArch,
    PAAction,
    PAStatus,
)
from tacticalrmm.test import TacticalTestCase
from logs.models import PendingAction


class TestAgentUpdate(TacticalTestCase):
    def setUp(self) -> None:
        self.authenticate()
        self.setup_coresettings()
        self.setup_base_instance()

    @patch("agents.management.commands.update_agents.send_agent_update_task.delay")
    @patch("agents.management.commands.update_agents.token_is_valid")
    @patch("agents.management.commands.update_agents.get_core_settings")
    def test_update_agents_mgmt_command(self, mock_core, mock_token, mock_update):
        mock_token.return_value = ("token123", True)

        baker.make_recipe(
            "agents.online_agent",
            site=self.site1,
            monitoring_type=AgentMonType.SERVER,
            plat=AgentPlat.WINDOWS,
            version="2.0.3",
            _quantity=6,
        )

        baker.make_recipe(
            "agents.online_agent",
            site=self.site3,
            monitoring_type=AgentMonType.WORKSTATION,
            plat=AgentPlat.LINUX,
            version="2.0.3",
            _quantity=5,
        )

        baker.make_recipe(
            "agents.online_agent",
            site=self.site2,
            monitoring_type=AgentMonType.SERVER,
            plat=AgentPlat.WINDOWS,
            version=settings.LATEST_AGENT_VER,
            _quantity=8,
        )

        mock_core.return_value.agent_auto_update = False
        call_command("update_agents")
        mock_update.assert_not_called()

        mock_core.return_value.agent_auto_update = True
        call_command("update_agents")

        ids = list(
            Agent.objects.defer(*AGENT_DEFER)
            .exclude(version=settings.LATEST_AGENT_VER)
            .values_list("agent_id", flat=True)
        )

        mock_update.assert_called_with(agent_ids=ids, token="token123", force=False)

    @patch("agents.models.Agent.nats_cmd")
    @patch("agents.models.get_agent_url")
    def test_do_update(self, mock_agent_url, mock_nats_cmd):
        mock_agent_url.return_value = "https://example.com/123"

        # test noarch
        agent_noarch = baker.make_recipe(
            "agents.online_agent",
            site=self.site1,
            monitoring_type=AgentMonType.SERVER,
            plat=AgentPlat.WINDOWS,
            version="2.3.0",
        )
        r = agent_noarch.do_update(token="", force=True)
        self.assertEqual(r, "noarch")

        # test too old
        agent_old = baker.make_recipe(
            "agents.online_agent",
            site=self.site2,
            monitoring_type=AgentMonType.SERVER,
            plat=AgentPlat.WINDOWS,
            version="1.3.0",
            goarch=GoArch.AMD64,
        )
        r = agent_old.do_update(token="", force=True)
        self.assertEqual(r, "not supported")

        win = baker.make_recipe(
            "agents.online_agent",
            site=self.site1,
            monitoring_type=AgentMonType.SERVER,
            plat=AgentPlat.WINDOWS,
            version="2.3.0",
            goarch=GoArch.AMD64,
        )

        lin = baker.make_recipe(
            "agents.online_agent",
            site=self.site3,
            monitoring_type=AgentMonType.WORKSTATION,
            plat=AgentPlat.LINUX,
            version="2.3.0",
            goarch=GoArch.ARM32,
        )

        # test windows agent update
        r = win.do_update(token="", force=False)
        self.assertEqual(r, "created")
        mock_nats_cmd.assert_called_with(
            {
                "func": "agentupdate",
                "payload": {
                    "url": "https://example.com/123",
                    "version": settings.LATEST_AGENT_VER,
                    "inno": f"tacticalagent-v{settings.LATEST_AGENT_VER}-windows-amd64.exe",
                },
            },
            wait=False,
        )
        action1 = PendingAction.objects.get(agent__agent_id=win.agent_id)
        self.assertEqual(action1.action_type, PAAction.AGENT_UPDATE)
        self.assertEqual(action1.status, PAStatus.PENDING)
        self.assertEqual(action1.details["url"], "https://example.com/123")
        self.assertEqual(
            action1.details["inno"],
            f"tacticalagent-v{settings.LATEST_AGENT_VER}-windows-amd64.exe",
        )
        self.assertEqual(action1.details["version"], settings.LATEST_AGENT_VER)

        mock_nats_cmd.reset_mock()

        # test linux agent update
        r = lin.do_update(token="", force=False)
        mock_nats_cmd.assert_called_with(
            {
                "func": "agentupdate",
                "payload": {
                    "url": "https://example.com/123",
                    "version": settings.LATEST_AGENT_VER,
                    "inno": f"tacticalagent-v{settings.LATEST_AGENT_VER}-linux-arm.exe",
                },
            },
            wait=False,
        )
        action2 = PendingAction.objects.get(agent__agent_id=lin.agent_id)
        self.assertEqual(action2.action_type, PAAction.AGENT_UPDATE)
        self.assertEqual(action2.status, PAStatus.PENDING)
        self.assertEqual(action2.details["url"], "https://example.com/123")
        self.assertEqual(
            action2.details["inno"],
            f"tacticalagent-v{settings.LATEST_AGENT_VER}-linux-arm.exe",
        )
        self.assertEqual(action2.details["version"], settings.LATEST_AGENT_VER)

        # check if old agent update pending actions are being deleted
        # should only be 1 pending action at all times
        pa_count = win.pendingactions.filter(
            action_type=PAAction.AGENT_UPDATE, status=PAStatus.PENDING
        ).count()
        self.assertEqual(pa_count, 1)

        for _ in range(4):
            win.do_update(token="", force=False)

        pa_count = win.pendingactions.filter(
            action_type=PAAction.AGENT_UPDATE, status=PAStatus.PENDING
        ).count()
        self.assertEqual(pa_count, 1)

    def test_auto_self_agent_update_task(self):
        auto_self_agent_update_task()

    @patch("agents.models.Agent.do_update")
    def test_send_agent_update_task(self, mock_update):
        baker.make_recipe(
            "agents.online_agent",
            site=self.site2,
            monitoring_type=AgentMonType.SERVER,
            plat=AgentPlat.WINDOWS,
            version="2.3.0",
            goarch=GoArch.AMD64,
            _quantity=6,
        )
        ids = list(
            Agent.objects.defer(*AGENT_DEFER)
            .exclude(version=settings.LATEST_AGENT_VER)
            .values_list("agent_id", flat=True)
        )
        send_agent_update_task(agent_ids=ids, token="", force=False)
        self.assertEqual(mock_update.call_count, 6)
