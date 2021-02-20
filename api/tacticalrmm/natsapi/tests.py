from django.conf import settings
from model_bakery import baker

from tacticalrmm.test import TacticalTestCase


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

    def test_natscheckin_patch(self):
        from logs.models import PendingAction

        url = "/natsapi/checkin/"
        agent_updated = baker.make_recipe("agents.agent", version="1.3.0")
        PendingAction.objects.create(
            agent=agent_updated,
            action_type="agentupdate",
            details={
                "url": agent_updated.winagent_dl,
                "version": agent_updated.version,
                "inno": agent_updated.win_inno_exe,
            },
        )
        action = agent_updated.pendingactions.filter(action_type="agentupdate").first()
        self.assertEqual(action.status, "pending")

        # test agent failed to update and still on same version
        payload = {
            "func": "hello",
            "agent_id": agent_updated.agent_id,
            "version": "1.3.0",
        }
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        action = agent_updated.pendingactions.filter(action_type="agentupdate").first()
        self.assertEqual(action.status, "pending")

        # test agent successful update
        payload["version"] = settings.LATEST_AGENT_VER
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, 200)
        action = agent_updated.pendingactions.filter(action_type="agentupdate").first()
        self.assertEqual(action.status, "completed")
        action.delete()
