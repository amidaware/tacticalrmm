from django.conf import settings
from model_bakery import baker

from tacticalrmm.test import TacticalTestCase


class TestNatsAPIViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_nats_agents(self):
        baker.make_recipe(
            "agents.online_agent", version=settings.LATEST_AGENT_VER, _quantity=14
        )

        baker.make_recipe(
            "agents.offline_agent", version=settings.LATEST_AGENT_VER, _quantity=6
        )
        baker.make_recipe(
            "agents.overdue_agent", version=settings.LATEST_AGENT_VER, _quantity=5
        )

        url = "/natsapi/online/agents/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["agent_ids"]), 14)

        url = "/natsapi/offline/agents/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["agent_ids"]), 11)

        url = "/natsapi/asdjaksdasd/agents/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
