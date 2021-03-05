import json
import os
from unittest.mock import patch

from django.conf import settings
from model_bakery import baker

from tacticalrmm.test import TacticalTestCase


class TestAPIv3(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()
        self.agent = baker.make_recipe("agents.agent")

    def test_get_checks(self):
        url = f"/api/v3/{self.agent.agent_id}/checkrunner/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        url = "/api/v3/Maj34ACb324j234asdj2n34kASDjh34-DESKTOPTEST123/checkrunner/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

        self.check_not_authenticated("get", url)

    def test_sysinfo(self):
        # TODO replace this with golang wmi sample data

        url = "/api/v3/sysinfo/"
        with open(
            os.path.join(
                settings.BASE_DIR, "tacticalrmm/test_data/wmi_python_agent.json"
            )
        ) as f:
            wmi_py = json.load(f)

        payload = {"agent_id": self.agent.agent_id, "sysinfo": wmi_py}

        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("patch", url)

    def test_checkrunner_interval(self):
        url = f"/api/v3/{self.agent.agent_id}/checkinterval/"
        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {"agent": self.agent.pk, "check_interval": self.agent.check_interval},
        )

    def test_checkin_patch(self):
        from logs.models import PendingAction

        url = "/api/v3/checkin/"
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

    @patch("apiv3.views.reload_nats")
    def test_agent_recovery(self, reload_nats):
        reload_nats.return_value = "ok"
        r = self.client.get("/api/v3/34jahsdkjasncASDjhg2b3j4r/recover/")
        self.assertEqual(r.status_code, 404)

        agent = baker.make_recipe("agents.online_agent")
        url = f"/api/v3/{agent.agent_id}/recovery/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"mode": "pass", "shellcmd": ""})
        reload_nats.assert_not_called()

        baker.make("agents.RecoveryAction", agent=agent, mode="mesh")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"mode": "mesh", "shellcmd": ""})
        reload_nats.assert_not_called()

        baker.make(
            "agents.RecoveryAction",
            agent=agent,
            mode="command",
            command="shutdown /r /t 5 /f",
        )
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(), {"mode": "command", "shellcmd": "shutdown /r /t 5 /f"}
        )
        reload_nats.assert_not_called()

        baker.make("agents.RecoveryAction", agent=agent, mode="rpc")
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"mode": "rpc", "shellcmd": ""})
        reload_nats.assert_called_once()
