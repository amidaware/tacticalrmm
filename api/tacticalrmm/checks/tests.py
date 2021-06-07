from unittest.mock import patch

from django.utils import timezone as djangotime
from model_bakery import baker

from checks.models import CheckHistory
from tacticalrmm.test import TacticalTestCase

from .serializers import CheckSerializer


class TestCheckViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_delete_agent_check(self):
        # setup data
        agent = baker.make_recipe("agents.agent")
        check = baker.make_recipe("checks.diskspace_check", agent=agent)

        resp = self.client.delete("/checks/500/check/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"/checks/{check.pk}/check/"

        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(agent.agentchecks.all())

        self.check_not_authenticated("delete", url)

    def test_get_disk_check(self):
        # setup data
        disk_check = baker.make_recipe("checks.diskspace_check")

        url = f"/checks/{disk_check.pk}/check/"

        resp = self.client.get(url, format="json")
        serializer = CheckSerializer(disk_check)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore
        self.check_not_authenticated("get", url)

    def test_add_disk_check(self):
        # setup data
        agent = baker.make_recipe("agents.agent")

        url = "/checks/checks/"

        valid_payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "C:",
                "error_threshold": 55,
                "warning_threshold": 0,
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
                "error_threshold": 55,
                "warning_threshold": 0,
                "fails_b4_alert": 3,
            },
        }

        resp = self.client.post(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        # this should fail because both error and warning threshold are 0
        invalid_payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "C:",
                "error_threshold": 0,
                "warning_threshold": 0,
                "fails_b4_alert": 3,
            },
        }

        resp = self.client.post(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        # this should fail because both error is greater than warning threshold
        invalid_payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "diskspace",
                "disk": "C:",
                "error_threshold": 50,
                "warning_threshold": 30,
                "fails_b4_alert": 3,
            },
        }

        resp = self.client.post(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("post", url)

    def test_add_cpuload_check(self):
        url = "/checks/checks/"
        agent = baker.make_recipe("agents.agent")
        payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "cpuload",
                "error_threshold": 66,
                "warning_threshold": 0,
                "fails_b4_alert": 9,
            },
        }

        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

        payload["error_threshold"] = 87
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["non_field_errors"][0],
            "A cpuload check for this agent already exists",
        )

        # should fail because both error and warning thresholds are 0
        invalid_payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "cpuload",
                "error_threshold": 0,
                "warning_threshold": 0,
                "fails_b4_alert": 9,
            },
        }

        resp = self.client.post(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        # should fail because error is less than warning
        invalid_payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "cpuload",
                "error_threshold": 10,
                "warning_threshold": 50,
                "fails_b4_alert": 9,
            },
        }

        resp = self.client.post(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("post", url)

    def test_add_memory_check(self):
        url = "/checks/checks/"
        agent = baker.make_recipe("agents.agent")
        payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "memory",
                "error_threshold": 78,
                "warning_threshold": 0,
                "fails_b4_alert": 1,
            },
        }

        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)

        payload["error_threshold"] = 55
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["non_field_errors"][0],
            "A memory check for this agent already exists",
        )

        # should fail because both error and warning thresholds are 0
        invalid_payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "memory",
                "error_threshold": 0,
                "warning_threshold": 0,
                "fails_b4_alert": 9,
            },
        }

        resp = self.client.post(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        # should fail because error is less than warning
        invalid_payload = {
            "pk": agent.pk,
            "check": {
                "check_type": "memory",
                "error_threshold": 10,
                "warning_threshold": 50,
                "fails_b4_alert": 9,
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
        self.assertEqual(resp.data, serializer.data)  # type: ignore
        self.check_not_authenticated("post", url)

    def test_add_policy_disk_check(self):
        # setup data
        policy = baker.make("automation.Policy")

        url = "/checks/checks/"

        valid_payload = {
            "policy": policy.pk,  # type: ignore
            "check": {
                "check_type": "diskspace",
                "disk": "M:",
                "error_threshold": 86,
                "warning_threshold": 0,
                "fails_b4_alert": 2,
            },
        }

        # should fail because both error and warning thresholds are 0
        invalid_payload = {
            "policy": policy.pk,  # type: ignore
            "check": {
                "check_type": "diskspace",
                "error_threshold": 0,
                "warning_threshold": 0,
                "fails_b4_alert": 9,
            },
        }

        resp = self.client.post(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

        # should fail because warning is less than error
        invalid_payload = {
            "policy": policy.pk,  # type: ignore
            "check": {
                "check_type": "diskspace",
                "error_threshold": 80,
                "warning_threshold": 50,
                "fails_b4_alert": 9,
            },
        }

        resp = self.client.post(url, valid_payload, format="json")
        self.assertEqual(resp.status_code, 200)

        # this should fail because we already have a check for drive M: in setup
        invalid_payload = {
            "policy": policy.pk,  # type: ignore
            "check": {
                "check_type": "diskspace",
                "disk": "M:",
                "error_threshold": 34,
                "warning_threshold": 0,
                "fails_b4_alert": 9,
            },
        }

        resp = self.client.post(url, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_get_disks_for_policies(self):
        url = "/checks/getalldisks/"
        r = self.client.get(url)
        self.assertIsInstance(r.data, list)  # type: ignore
        self.assertEqual(26, len(r.data))  # type: ignore

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
        agent_b4_141 = baker.make_recipe("agents.agent", version="1.4.0")

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
        baker.make("checks.CheckHistory", check_id=check.id, _quantity=30)
        check_history_data = baker.make(
            "checks.CheckHistory",
            check_id=check.id,
            _quantity=30,
        )

        # need to manually set the date back 35 days
        for check_history in check_history_data:  # type: ignore
            check_history.x = djangotime.now() - djangotime.timedelta(days=35)  # type: ignore
            check_history.save()

        # test invalid check pk
        resp = self.client.patch("/checks/history/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"/checks/history/{check.id}/"

        # test with timeFilter last 30 days
        data = {"timeFilter": 30}
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 30)  # type: ignore

        # test with timeFilter equal to 0
        data = {"timeFilter": 0}
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 60)  # type: ignore

        self.check_not_authenticated("patch", url)


class TestCheckTasks(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()
        self.agent = baker.make_recipe("agents.agent", version="1.5.7")

    def test_prune_check_history(self):
        from .tasks import prune_check_history

        # setup data
        check = baker.make_recipe("checks.diskspace_check")
        baker.make("checks.CheckHistory", check_id=check.id, _quantity=30)
        check_history_data = baker.make(
            "checks.CheckHistory",
            check_id=check.id,
            _quantity=30,
        )

        # need to manually set the date back 35 days
        for check_history in check_history_data:  # type: ignore
            check_history.x = djangotime.now() - djangotime.timedelta(days=35)  # type: ignore
            check_history.save()

        # prune data 30 days old
        prune_check_history(30)
        self.assertEqual(CheckHistory.objects.count(), 30)

        # prune all Check history Data
        prune_check_history(0)
        self.assertEqual(CheckHistory.objects.count(), 0)

    def test_handle_script_check(self):
        from checks.models import Check

        url = "/api/v3/checkrunner/"

        script = baker.make_recipe("checks.script_check", agent=self.agent)

        # test failing
        data = {
            "id": script.id,
            "retcode": 500,
            "stderr": "error",
            "stdout": "message",
            "runtime": 5.000,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=script.id)

        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")

        # test passing
        data = {
            "id": script.id,
            "retcode": 0,
            "stderr": "error",
            "stdout": "message",
            "runtime": 5.000,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=script.id)

        self.assertEqual(new_check.status, "passing")

        # test failing info
        script.info_return_codes = [20, 30, 50]
        script.save()

        data = {
            "id": script.id,
            "retcode": 30,
            "stderr": "error",
            "stdout": "message",
            "runtime": 5.000,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=script.id)

        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "info")

        # test failing warning
        script.warning_return_codes = [80, 100, 1040]
        script.save()

        data = {
            "id": script.id,
            "retcode": 1040,
            "stderr": "error",
            "stdout": "message",
            "runtime": 5.000,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=script.id)

        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "warning")

    def test_handle_diskspace_check(self):
        from checks.models import Check

        url = "/api/v3/checkrunner/"

        diskspace = baker.make_recipe(
            "checks.diskspace_check",
            warning_threshold=20,
            error_threshold=10,
            agent=self.agent,
        )

        # test warning threshold failure
        data = {
            "id": diskspace.id,
            "exists": True,
            "percent_used": 85,
            "total": 500,
            "free": 400,
            "more_info": "More info",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=diskspace.id)

        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "warning")

        # test error failure
        data = {
            "id": diskspace.id,
            "exists": True,
            "percent_used": 95,
            "total": 500,
            "free": 400,
            "more_info": "More info",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=diskspace.id)

        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")

        # test disk not exist
        data = {"id": diskspace.id, "exists": False}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=diskspace.id)

        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")

        # test warning threshold 0
        diskspace.warning_threshold = 0
        diskspace.save()
        data = {
            "id": diskspace.id,
            "exists": True,
            "percent_used": 95,
            "total": 500,
            "free": 400,
            "more_info": "More info",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=diskspace.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")

        # test error threshold 0
        diskspace.warning_threshold = 50
        diskspace.error_threshold = 0
        diskspace.save()
        data = {
            "id": diskspace.id,
            "exists": True,
            "percent_used": 95,
            "total": 500,
            "free": 400,
            "more_info": "More info",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=diskspace.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "warning")

        # test passing
        data = {
            "id": diskspace.id,
            "exists": True,
            "percent_used": 50,
            "total": 500,
            "free": 400,
            "more_info": "More info",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=diskspace.id)

        self.assertEqual(new_check.status, "passing")

    def test_handle_cpuload_check(self):
        from checks.models import Check

        url = "/api/v3/checkrunner/"

        cpuload = baker.make_recipe(
            "checks.cpuload_check",
            warning_threshold=70,
            error_threshold=90,
            agent=self.agent,
        )

        # test failing warning
        data = {"id": cpuload.id, "percent": 80}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=cpuload.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "warning")

        # test failing error
        data = {"id": cpuload.id, "percent": 95}

        # reset check history
        cpuload.history = []
        cpuload.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=cpuload.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")

        # test passing
        data = {"id": cpuload.id, "percent": 50}

        # reset check history
        cpuload.history = []
        cpuload.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=cpuload.id)
        self.assertEqual(new_check.status, "passing")

        # test warning threshold 0
        cpuload.warning_threshold = 0
        cpuload.save()
        data = {"id": cpuload.id, "percent": 95}

        # reset check history
        cpuload.history = []
        cpuload.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=cpuload.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")

        # test error threshold 0
        cpuload.warning_threshold = 50
        cpuload.error_threshold = 0
        cpuload.save()
        data = {"id": cpuload.id, "percent": 95}

        # reset check history
        cpuload.history = []
        cpuload.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=cpuload.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "warning")

    def test_handle_memory_check(self):
        from checks.models import Check

        url = "/api/v3/checkrunner/"

        memory = baker.make_recipe(
            "checks.memory_check",
            warning_threshold=70,
            error_threshold=90,
            agent=self.agent,
        )

        # test failing warning
        data = {"id": memory.id, "percent": 80}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=memory.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "warning")

        # test failing error
        data = {"id": memory.id, "percent": 95}

        # reset check history
        memory.history = []
        memory.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=memory.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")

        # test passing
        data = {"id": memory.id, "percent": 50}

        # reset check history
        memory.history = []
        memory.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=memory.id)
        self.assertEqual(new_check.status, "passing")

        # test warning threshold 0
        memory.warning_threshold = 0
        memory.save()
        data = {"id": memory.id, "percent": 95}

        # reset check history
        memory.history = []
        memory.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=memory.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")

        # test error threshold 0
        memory.warning_threshold = 50
        memory.error_threshold = 0
        memory.save()
        data = {"id": memory.id, "percent": 95}

        # reset check history
        memory.history = []
        memory.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=memory.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "warning")

    def test_handle_ping_check(self):
        from checks.models import Check

        url = "/api/v3/checkrunner/"

        ping = baker.make_recipe(
            "checks.ping_check", agent=self.agent, alert_severity="info"
        )

        # test failing info
        data = {"id": ping.id, "status": "failing", "output": "reply from a.com"}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=ping.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "info")

        # test failing warning
        ping.alert_severity = "warning"
        ping.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=ping.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "warning")

        # test failing error
        ping.alert_severity = "error"
        ping.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=ping.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")

        # test failing error
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=ping.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")

        # test passing
        data = {"id": ping.id, "status": "passing", "output": "reply from a.com"}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=ping.id)
        self.assertEqual(new_check.status, "passing")

    @patch("agents.models.Agent.nats_cmd")
    def test_handle_winsvc_check(self, nats_cmd):
        from checks.models import Check

        url = "/api/v3/checkrunner/"

        winsvc = baker.make_recipe(
            "checks.winsvc_check", agent=self.agent, alert_severity="info"
        )

        # test passing running
        data = {"id": winsvc.id, "status": "passing", "more_info": "ok"}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=winsvc.id)
        self.assertEqual(new_check.status, "passing")

        # test failing
        data = {"id": winsvc.id, "status": "failing", "more_info": "ok"}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=winsvc.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "info")

        """ # test failing and attempt start
        winsvc.restart_if_stopped = True
        winsvc.alert_severity = "warning"
        winsvc.save()

        nats_cmd.return_value = "timeout"

        data = {"id": winsvc.id, "exists": True, "status": "not running"}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=winsvc.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "warning")
        nats_cmd.assert_called()
        nats_cmd.reset_mock()

        # test failing and attempt start
        winsvc.alert_severity = "error"
        winsvc.save()
        nats_cmd.return_value = {"success": False, "errormsg": "Some Error"}

        data = {"id": winsvc.id, "exists": True, "status": "not running"}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=winsvc.id)
        self.assertEqual(new_check.status, "failing")
        self.assertEqual(new_check.alert_severity, "error")
        nats_cmd.assert_called()
        nats_cmd.reset_mock()

        # test success and attempt start
        nats_cmd.return_value = {"success": True}

        data = {"id": winsvc.id, "exists": True, "status": "not running"}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=winsvc.id)
        self.assertEqual(new_check.status, "passing")
        nats_cmd.assert_called()
        nats_cmd.reset_mock()

        # test failing and service not exist
        data = {"id": winsvc.id, "exists": False, "status": ""}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=winsvc.id)
        self.assertEqual(new_check.status, "failing")

        # test success and service not exist
        winsvc.pass_if_svc_not_exist = True
        winsvc.save()
        data = {"id": winsvc.id, "exists": False, "status": ""}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=winsvc.id)
        self.assertEqual(new_check.status, "passing") """

    """ def test_handle_eventlog_check(self):
        from checks.models import Check

        url = "/api/v3/checkrunner/"

        eventlog = baker.make_recipe(
            "checks.eventlog_check",
            event_type="warning",
            fail_when="contains",
            event_id=123,
            alert_severity="warning",
            agent=self.agent,
        )

        data = {
            "id": eventlog.id,
            "log": [
                {
                    "eventType": "warning",
                    "eventID": 150,
                    "source": "source",
                    "message": "a test message",
                },
                {
                    "eventType": "warning",
                    "eventID": 123,
                    "source": "source",
                    "message": "a test message",
                },
                {
                    "eventType": "error",
                    "eventID": 123,
                    "source": "source",
                    "message": "a test message",
                },
                {
                    "eventType": "error",
                    "eventID": 123,
                    "source": "source",
                    "message": "a test message",
                },
            ],
        }

        # test failing when contains
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.alert_severity, "warning")
        self.assertEquals(new_check.status, "failing")

        # test passing when not contains and message
        eventlog.event_message = "doesnt exist"
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "passing")

        # test failing when not contains and message and source
        eventlog.fail_when = "not_contains"
        eventlog.alert_severity = "error"
        eventlog.event_message = "doesnt exist"
        eventlog.event_source = "doesnt exist"
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "failing")
        self.assertEquals(new_check.alert_severity, "error")

        # test passing when contains with source and message
        eventlog.event_message = "test"
        eventlog.event_source = "source"
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "passing")

        # test failing with wildcard not contains and source
        eventlog.event_id_is_wildcard = True
        eventlog.event_source = "doesn't exist"
        eventlog.event_message = ""
        eventlog.event_id = 0
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "failing")
        self.assertEquals(new_check.alert_severity, "error")

        # test passing with wildcard contains
        eventlog.event_source = ""
        eventlog.event_message = ""
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "passing")

        # test failing with wildcard contains and message
        eventlog.fail_when = "contains"
        eventlog.event_type = "error"
        eventlog.alert_severity = "info"
        eventlog.event_message = "test"
        eventlog.event_source = ""
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "failing")
        self.assertEquals(new_check.alert_severity, "info")

        # test passing with wildcard not contains message and source
        eventlog.event_message = "doesnt exist"
        eventlog.event_source = "doesnt exist"
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "passing")

        # test multiple events found and contains
        # this should pass since only two events are found
        eventlog.number_of_events_b4_alert = 3
        eventlog.event_id_is_wildcard = False
        eventlog.event_source = None
        eventlog.event_message = None
        eventlog.event_id = 123
        eventlog.event_type = "error"
        eventlog.fail_when = "contains"
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "passing")

        # this should pass since there are two events returned
        eventlog.number_of_events_b4_alert = 2
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "failing")

        # test not contains
        # this should fail since only two events are found
        eventlog.number_of_events_b4_alert = 3
        eventlog.event_id_is_wildcard = False
        eventlog.event_source = None
        eventlog.event_message = None
        eventlog.event_id = 123
        eventlog.event_type = "error"
        eventlog.fail_when = "not_contains"
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "failing")

        # this should pass since there are two events returned
        eventlog.number_of_events_b4_alert = 2
        eventlog.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "passing") """
