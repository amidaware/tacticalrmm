from checks.models import CheckHistory
from tacticalrmm.test import TacticalTestCase
from .serializers import CheckSerializer
from django.utils import timezone as djangotime
from unittest.mock import patch

from model_bakery import baker


class TestCheckViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

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

    def test_add_cpuload_check(self):
        url = "/checks/checks/"
        agent = baker.make_recipe("agents.agent")
        payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "cpuload",
                "threshold": 66,
                "fails_b4_alert": 9,
            },
        }

        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

        payload["threshold"] = 87
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["non_field_errors"][0],
            "A cpuload check for this agent already exists",
        )

    def test_add_memory_check(self):
        url = "/checks/checks/"
        agent = baker.make_recipe("agents.agent")
        payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "memory",
                "threshold": 78,
                "fails_b4_alert": 1,
            },
        }

        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

        payload["threshold"] = 55
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["non_field_errors"][0],
            "A memory check for this agent already exists",
        )

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

    @patch("agents.models.Agent.nats_cmd")
    def test_run_checks(self, nats_cmd):
        agent = baker.make_recipe("agents.agent", version="1.4.1")
        agent_old = baker.make_recipe("agents.agent", version="1.0.2")
        agent_b4_141 = baker.make_recipe("agents.agent", version="1.4.0")

        url = f"/checks/runchecks/{agent_old.pk}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), "Requires agent version 1.1.0 or greater")

        url = f"/checks/runchecks/{agent_b4_141.pk}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_with({"func": "runchecks"}, wait=False)

        nats_cmd.reset_mock()
        nats_cmd.return_value = "busy"
        url = f"/checks/runchecks/{agent.pk}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
        nats_cmd.assert_called_with({"func": "runchecks"}, timeout=15)
        self.assertEqual(r.json(), f"Checks are already running on {agent.hostname}")

        nats_cmd.reset_mock()
        nats_cmd.return_value = "ok"
        url = f"/checks/runchecks/{agent.pk}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_with({"func": "runchecks"}, timeout=15)
        self.assertEqual(r.json(), f"Checks will now be re-run on {agent.hostname}")

        nats_cmd.reset_mock()
        nats_cmd.return_value = "timeout"
        url = f"/checks/runchecks/{agent.pk}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
        nats_cmd.assert_called_with({"func": "runchecks"}, timeout=15)
        self.assertEqual(r.json(), "Unable to contact the agent")

        self.check_not_authenticated("get", url)

    def test_get_check_history(self):
        # setup data
        agent = baker.make_recipe("agents.agent")
        check = baker.make_recipe("checks.diskspace_check", agent=agent)
        baker.make("checks.CheckHistory", check_history=check, _quantity=30)
        check_history_data = baker.make(
            "checks.CheckHistory",
            check_history=check,
            _quantity=30,
        )

        # need to manually set the date back 35 days
        for check_history in check_history_data:
            check_history.x = djangotime.now() - djangotime.timedelta(days=35)
            check_history.save()

        # test invalid check pk
        resp = self.client.patch("/checks/history/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"/checks/history/{check.id}/"

        # test with timeFilter last 30 days
        data = {"timeFilter": 30}
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 30)

        # test with timeFilter equal to 0
        data = {"timeFilter": 0}
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 60)

        self.check_not_authenticated("patch", url)


class TestCheckTasks(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()

    def test_prune_check_history(self):
        from .tasks import prune_check_history

        # setup data
        check = baker.make_recipe("checks.diskspace_check")
        baker.make("checks.CheckHistory", check_history=check, _quantity=30)
        check_history_data = baker.make(
            "checks.CheckHistory",
            check_history=check,
            _quantity=30,
        )

        # need to manually set the date back 35 days
        for check_history in check_history_data:
            check_history.x = djangotime.now() - djangotime.timedelta(days=35)
            check_history.save()

        # prune data 30 days old
        prune_check_history(30)
        self.assertEqual(CheckHistory.objects.count(), 30)

        # prune all Check history Data
        prune_check_history(0)
        self.assertEqual(CheckHistory.objects.count(), 0)
