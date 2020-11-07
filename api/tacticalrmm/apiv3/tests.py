import os
import json

from django.conf import settings
from tacticalrmm.test import TacticalTestCase
from unittest.mock import patch
from model_bakery import baker
from itertools import cycle


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

    def test_get_salt_minion(self):
        url = f"/api/v3/{self.agent.agent_id}/saltminion/"
        url2 = f"/api/v2/{self.agent.agent_id}/saltminion/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn("latestVer", r.json().keys())
        self.assertIn("currentVer", r.json().keys())
        self.assertIn("salt_id", r.json().keys())
        self.assertIn("downloadURL", r.json().keys())

        r2 = self.client.get(url2)
        self.assertEqual(r2.status_code, 200)

        self.check_not_authenticated("get", url)
        self.check_not_authenticated("get", url2)

    def test_get_mesh_info(self):
        url = f"/api/v3/{self.agent.pk}/meshinfo/"
        url2 = f"/api/v1/{self.agent.pk}/meshinfo/"

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        r = self.client.get(url2)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)
        self.check_not_authenticated("get", url2)

    def test_get_winupdater(self):
        url = f"/api/v3/{self.agent.agent_id}/winupdater/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("get", url)

    def test_sysinfo(self):
        # TODO replace this with golang wmi sample data

        url = f"/api/v3/sysinfo/"
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

    def test_hello_patch(self):
        url = f"/api/v3/hello/"
        payload = {
            "agent_id": self.agent.agent_id,
            "logged_in_username": "None",
            "disks": [],
        }

        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        payload["logged_in_username"] = "Bob"
        r = self.client.patch(url, payload, format="json")
        self.assertEqual(r.status_code, 200)

        self.check_not_authenticated("patch", url)
