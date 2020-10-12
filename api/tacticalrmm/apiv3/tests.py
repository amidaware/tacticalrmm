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
