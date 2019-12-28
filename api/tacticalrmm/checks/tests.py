from tacticalrmm.test import BaseTestCase
from .serializers import CheckSerializer


class TestCheckViews(BaseTestCase):
    def test_add_disk_check(self):
        disk_data = {
            "pk": self.agent.pk,
            "check_type": "diskspace",
            "disk": "C:",
            "threshold": 41,
        }
        resp = self.client.post("/checks/addstandardcheck/", disk_data, format="json")
        self.assertEqual(resp.status_code, 200)
        data = CheckSerializer(self.agent).data
        self.assertEqual(data["diskchecks"][0]["threshold"], 41)
