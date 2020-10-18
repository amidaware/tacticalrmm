from tacticalrmm.test import BaseTestCase
from unittest.mock import patch


class TestAPIv3(BaseTestCase):
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
