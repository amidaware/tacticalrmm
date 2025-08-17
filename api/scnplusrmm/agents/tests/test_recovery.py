from typing import TYPE_CHECKING
from unittest.mock import patch

from model_bakery import baker

from tacticalrmm.constants import AgentMonType, AgentPlat
from tacticalrmm.test import TacticalTestCase

if TYPE_CHECKING:
    from clients.models import Client, Site


class TestRecovery(TacticalTestCase):
    def setUp(self) -> None:
        self.authenticate()
        self.setup_coresettings()
        self.client1: "Client" = baker.make("clients.Client")
        self.site1: "Site" = baker.make("clients.Site", client=self.client1)

    @patch("agents.models.Agent.recover")
    @patch("agents.views.get_mesh_ws_url")
    def test_recover(self, get_mesh_ws_url, recover) -> None:
        get_mesh_ws_url.return_value = "https://mesh.example.com"

        agent = baker.make_recipe(
            "agents.online_agent",
            site=self.site1,
            monitoring_type=AgentMonType.SERVER,
            plat=AgentPlat.WINDOWS,
        )

        url = f"/agents/{agent.agent_id}/recover/"

        # test successfull tacticalagent recovery
        data = {"mode": "tacagent"}
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        recover.assert_called_with("tacagent", "https://mesh.example.com", wait=False)
        get_mesh_ws_url.assert_called_once()

        # reset mocks
        recover.reset_mock()
        get_mesh_ws_url.reset_mock()

        # test successfull mesh agent recovery
        data = {"mode": "mesh"}
        recover.return_value = ("ok", False)
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        get_mesh_ws_url.assert_not_called()
        recover.assert_called_with("mesh", "")

        # reset mocks
        recover.reset_mock()
        get_mesh_ws_url.reset_mock()

        # test failed mesh agent recovery
        data = {"mode": "mesh"}
        recover.return_value = ("Unable to contact the agent", True)
        r = self.client.post(url, data, format="json")
        self.assertEqual(r.status_code, 400)

        self.check_not_authenticated("post", url)
