from tacticalrmm.test import TacticalTestCase
from unittest.mock import patch
from model_bakery import baker
from itertools import cycle


class TestAPIv2(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    @patch("agents.models.Agent.salt_api_cmd")
    def test_sync_modules(self, mock_ret):
        # setup data
        agent = baker.make_recipe("agents.agent")
        url = "/api/v2/saltminion/"
        payload = {"agent_id": agent.agent_id}

        mock_ret.return_value = "error"
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, 400)

        mock_ret.return_value = []
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, "Modules are already in sync")

        mock_ret.return_value = ["modules.win_agent"]
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, "Successfully synced salt modules")

        mock_ret.return_value = ["askdjaskdjasd", "modules.win_agent"]
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, "Successfully synced salt modules")

        self.check_not_authenticated("patch", url)
