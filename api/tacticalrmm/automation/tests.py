from rest_framework import status
from django.urls import reverse

from tacticalrmm.test import BaseTestCase
from .serializers import PolicyTableSerializer, PolicySerializer

from unittest.mock import patch


class TestPolicyViews(BaseTestCase):
    def test_get_all_policies(self):
        url = "/automation/policies/"

        resp = self.client.get(url, format="json")
        serializer = PolicyTableSerializer([self.policy], many=True)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("get", url)

    def test_get_policy(self):
        url = f"/automation/policies/{self.policy.pk}/"

        resp = self.client.get(url, format="json")
        serializer = PolicySerializer(self.policy)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)

        # returns 404 for invalid policy pk
        resp = self.client.get("/automation/policies/500/", format="json")
        self.assertEqual(resp.status_code, 404)
        self.check_not_authenticated("get", "/automation/policies/500/")

    def test_add_policy(self):
        url = "/automation/policies/"

        valid_payload = {
            "name": "Test Policy",
            "desc": "policy desc",
            "active": True,
            "enforced": False
        }

        resp = self.client.post(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # running again should fail since names are unique
        resp = self.client.post(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("post", url)

    @patch('automation.tasks.generate_agent_checks_from_policies_task.delay')
    def test_update_policy(self, mock_task):
        url = f"/automation/policies/{self.policy.pk}/"

        valid_payload = {
            "name": "Test Policy Update",
            "desc": "policy desc Update",
            "active": True,
            "enforced": False
        }

        resp = self.client.put(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # only called if active or enforced are updated
        mock_task.assert_not_called()

        valid_payload = {
            "name": "Test Policy Update",
            "desc": "policy desc Update",
            "active": False,
            "enforced": False
        }

        resp = self.client.put(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_task.assert_called_with(policypk=self.policy.pk)

        self.check_not_authenticated("put", url)
