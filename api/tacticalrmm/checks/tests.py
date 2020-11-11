from tacticalrmm.test import TacticalTestCase
from .serializers import CheckSerializer

from model_bakery import baker
from itertools import cycle


class TestCheckViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()

    def test_get_disk_check(self):
        # setup data
        disk_check = baker.make_recipe("checks.diskspace_check")

        url = f"/checks/{disk_check.pk}/check/"

        resp = self.client.get(url, format="json")
        serializer = CheckSerializer(disk_check)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("post", url)

    def test_add_disk_check(self):
        # setup data
        agent = baker.make_recipe("agents.agent")

        url = "/checks/checks/"

        valid_payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "C:",
                "threshold": 55,
                "fails_b4_alert": 3,
            },
        }

        resp = self.client.post(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # this should fail because we already have a check for drive C: in setup
        invalid_payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "C:",
                "threshold": 55,
                "fails_b4_alert": 3,
            },
        }

        resp = self.client.post(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_get_policy_disk_check(self):
        # setup data
        policy = baker.make("automation.Policy")
        disk_check = baker.make_recipe("checks.diskspace_check", policy=policy)

        url = f"/checks/{disk_check.pk}/check/"

        resp = self.client.get(url, format="json")
        serializer = CheckSerializer(disk_check)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("post", url)

    def test_add_policy_disk_check(self):
        # setup data
        policy = baker.make("automation.Policy")

        url = "/checks/checks/"

        valid_payload = {
            "policy": policy.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "M:",
                "threshold": 86,
                "fails_b4_alert": 2,
            },
        }

        resp = self.client.post(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # this should fail because we already have a check for drive M: in setup
        invalid_payload = {
            "policy": policy.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "M:",
                "threshold": 34,
                "fails_b4_alert": 9,
            },
        }

        resp = self.client.post(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_get_disks_for_policies(self):
        url = "/checks/getalldisks/"
        r = self.client.get(url)
        self.assertIsInstance(r.data, list)
        self.assertEqual(26, len(r.data))

    def test_edit_check_alert(self):
        # setup data
        policy = baker.make("automation.Policy")
        agent = baker.make_recipe("agents.agent")

        policy_disk_check = baker.make_recipe("checks.diskspace_check", policy=policy)
        agent_disk_check = baker.make_recipe("checks.diskspace_check", agent=agent)
        url_a = f"/checks/{agent_disk_check.pk}/check/"
        url_p = f"/checks/{policy_disk_check.pk}/check/"

        valid_payload = {"email_alert": False, "check_alert": True}
        invalid_payload = {"email_alert": False}

        with self.assertRaises(KeyError) as err:
            resp = self.client.patch(url_a, invalid_payload, format="json")

        with self.assertRaises(KeyError) as err:
            resp = self.client.patch(url_p, invalid_payload, format="json")

        resp = self.client.patch(url_a, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.patch(url_p, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("patch", url_a)
