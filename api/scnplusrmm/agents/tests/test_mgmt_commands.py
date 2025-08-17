from unittest.mock import call, patch

from django.core.management import call_command
from model_bakery import baker

from tacticalrmm.constants import AgentMonType, AgentPlat
from tacticalrmm.test import TacticalTestCase


class TestBulkRestartAgents(TacticalTestCase):
    def setUp(self) -> None:
        self.authenticate()
        self.setup_coresettings()
        self.setup_base_instance()

    @patch("core.management.commands.bulk_restart_agents.sleep")
    @patch("agents.models.Agent.recover")
    @patch("core.management.commands.bulk_restart_agents.get_mesh_ws_url")
    def test_bulk_restart_agents_mgmt_cmd(
        self, get_mesh_ws_url, recover, mock_sleep
    ) -> None:
        get_mesh_ws_url.return_value = "https://mesh.example.com/test"

        baker.make_recipe(
            "agents.online_agent",
            site=self.site1,
            monitoring_type=AgentMonType.SERVER,
            plat=AgentPlat.WINDOWS,
        )

        baker.make_recipe(
            "agents.online_agent",
            site=self.site3,
            monitoring_type=AgentMonType.SERVER,
            plat=AgentPlat.LINUX,
        )

        calls = [
            call("tacagent", "https://mesh.example.com/test", wait=False),
            call("mesh", "", wait=False),
        ]

        call_command("bulk_restart_agents")

        recover.assert_has_calls(calls)
        mock_sleep.assert_called_with(10)
