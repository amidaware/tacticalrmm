from rest_framework import status
from django.urls import reverse

from tacticalrmm.test import BaseTestCase
from .serializers import CheckSerializer


class TestCheckViews(BaseTestCase):
    def test_get_disk_check(self):
        url = f"/checks/{self.agentDiskCheck.pk}/check/"

        resp = self.client.get(url, format="json")
        serializer = CheckSerializer(self.agentDiskCheck)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("post", url)

    def test_add_diskcheck(self):
        url = "/checks/checks/"

        self.valid_payload = {
            "pk": self.agent.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "D:",
                "threshold": 55,
                "fails_b4_alert": 3,
            },
        }

        resp = self.client.post(url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # this should fail because we already have a check for drive C: in setup
        self.invalid_payload = {
            "pk": self.agent.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "C:",
                "threshold": 55,
                "fails_b4_alert": 3,
            },
        }

        resp = self.client.post(url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_get_policy_disk_check(self):
        url = f"/checks/{self.policyDiskCheck.pk}/check/"

        resp = self.client.get(url, format="json")
        serializer = CheckSerializer(self.policyDiskCheck)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("post", url)

    def test_add_policy_diskcheck(self):
        url = "/checks/checks/"

        self.valid_payload = {
            "pk": self.policy.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "D:",
                "threshold": 86,
                "fails_b4_alert": 2,
            },
        }

        resp = self.client.post(url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # this should fail because we already have a check for drive M: in setup
        self.invalid_payload = {
            "pk": self.policy.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "M:",
                "threshold": 34,
                "fails_b4_alert": 9,
            },
        }

        resp = self.client.post(url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_get_disks_for_policies(self):
        url = "/checks/getalldisks/"
        r = self.client.get(url)
        self.assertIsInstance(r.data, list)
        self.assertEqual(26, len(r.data))
