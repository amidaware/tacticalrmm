from tacticalrmm.test import BaseTestCase
from .serializers import CheckSerializer  # , PolicyChecksSerializer


class TestCheckViews(BaseTestCase):
    def test_add_disk_check(self):
        url = "/checks/"
        disk_data = {
            "pk": self.agent.pk,
            "check_type": "diskspace",
            "disk": "C:",
            "threshold": 41,
            "failure": 4,
        }
        resp = self.client.post(url, disk_data, format="json")
        self.assertEqual(resp.status_code, 200)
        data = CheckSerializer(self.agent).data
        self.assertEqual(data["diskchecks"][0]["threshold"], 41)
        self.assertEqual(data["diskchecks"][0]["failures"], 4)
        self.assertEqual(data["diskchecks"][0]["disk"], "C:")

        self.check_not_authenticated("post", url)

    def test_add_policy_disk_check(self):
        url = "/checks/"
        policy_disk_data = {
            "policy": self.policy.pk,
            "check_type": "diskspace",
            "disk": "M:",
            "threshold": 87,
            "failure": 1,
        }
        resp = self.client.post(url, policy_disk_data, format="json")
        self.assertEqual(resp.status_code, 200)
        data = CheckSerializer(self.policy).data
        self.assertEqual(data["diskchecks"][0]["threshold"], 87)
        self.assertEqual(data["diskchecks"][0]["failures"], 1)
        self.assertEqual(data["diskchecks"][0]["disk"], "M:")

        self.check_not_authenticated("post", url)

    def test_get_disks_for_policies(self):
        url = "/checks/getalldisks/"
        r = self.client.get(url)
        self.assertIsInstance(r.data, list)
        self.assertEqual(26, len(r.data))
