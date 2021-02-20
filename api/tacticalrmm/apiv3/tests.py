import json
import os
from itertools import cycle
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
