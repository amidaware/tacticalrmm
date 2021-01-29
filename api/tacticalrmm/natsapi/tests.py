from model_bakery import baker
from tacticalrmm.test import TacticalTestCase
from django.conf import settings


class TestNatsAPIViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_nats_wmi(self):
        url = "/natsapi/wmi/"
        baker.make_recipe("agents.online_agent", version="1.2.0", _quantity=14)
        baker.make_recipe(
            "agents.online_agent", version=settings.LATEST_AGENT_VER, _quantity=3
        )
        baker.make_recipe(
            "agents.overdue_agent", version=settings.LATEST_AGENT_VER, _quantity=5
        )
        baker.make_recipe("agents.online_agent", version="1.1.12", _quantity=7)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["agent_ids"]), 17)
