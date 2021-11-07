from unittest.mock import patch

from django.utils import timezone as djangotime
from model_bakery import baker

from checks.models import CheckHistory
from tacticalrmm.test import TacticalTestCase

from .serializers import CheckSerializer

base_url = "/checks"


class TestCheckViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def test_get_checks(self):
        url = f"{base_url}/"
        agent = baker.make_recipe("agents.agent")
        baker.make("checks.Check", agent=agent, _quantity=4)
        baker.make("checks.Check", _quantity=4)

        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 8)  # type: ignore

        # test checks agent url
        url = f"/agents/{agent.agent_id}/checks/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 4)  # type: ignore

        # test agent doesn't exist
        url = f"/agents/jh3498uf8fkh4ro8hfd8df98/checks/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 404)

        self.check_not_authenticated("get", url)

    def test_delete_agent_check(self):
        # setup data
        agent = baker.make_recipe("agents.agent")
        check = baker.make_recipe("checks.diskspace_check", agent=agent)

        resp = self.client.delete(f"{base_url}/500/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"{base_url}/{check.pk}/"

        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(agent.agentchecks.all())

        self.check_not_authenticated("delete", url)

    def test_get_check(self):
        # setup data
        disk_check = baker.make_recipe("checks.diskspace_check")

        url = f"{base_url}/{disk_check.pk}/"

        resp = self.client.get(url, format="json")
        serializer = CheckSerializer(disk_check)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, serializer.data)  # type: ignore
        self.check_not_authenticated("get", url)

    def test_add_disk_check(self):
        # setup data
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")

        url = f"{base_url}/"

        agent_payload = {
            "agent": agent.agent_id,
            "check_type": "diskspace",
            "disk": "C:",
            "error_threshold": 55,
            "warning_threshold": 0,
            "fails_b4_alert": 3,
        }

        policy_payload = {
            "policy": policy.id,
            "check_type": "diskspace",
            "disk": "C:",
            "error_threshold": 55,
            "warning_threshold": 0,
            "fails_b4_alert": 3,
        }

        for payload in [agent_payload, policy_payload]:

            # add valid check
            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 200)

            # this should fail since we just added it
            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 400)

            # this should fail because both error and warning threshold are 0
            payload["error_threshold"] = 0
            payload["warning_threshold"] = 0

            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 400)

            # this should fail because error threshold is greater than warning threshold
            payload["error_threshold"] = 50
            payload["warning_threshold"] = 30

            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("post", url)

    def test_add_cpuload_check(self):
        url = f"{base_url}/"
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")

        agent_payload = {
            "agent": agent.agent_id,
            "check_type": "cpuload",
            "error_threshold": 66,
            "warning_threshold": 0,
            "fails_b4_alert": 9,
        }

        policy_payload = {
            "policy": policy.id,
            "check_type": "cpuload",
            "error_threshold": 66,
            "warning_threshold": 0,
            "fails_b4_alert": 9,
        }

        for payload in [agent_payload, policy_payload]:

            # add cpu check
            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 200)

            # should fail since cpu check already exists
            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 400)

            # this should fail because both error and warning threshold are 0
            payload["error_threshold"] = 0
            payload["warning_threshold"] = 0

            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 400)

            # this should fail because error threshold is less than warning threshold
            payload["error_threshold"] = 20
            payload["warning_threshold"] = 30

            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("post", url)

    def test_add_memory_check(self):
        url = f"{base_url}/"
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")

        agent_payload = {
            "agent": agent.agent_id,
            "check_type": "memory",
            "error_threshold": 78,
            "warning_threshold": 0,
            "fails_b4_alert": 1,
        }

        policy_payload = {
            "policy": policy.id,
            "check_type": "memory",
            "error_threshold": 78,
            "warning_threshold": 0,
            "fails_b4_alert": 1,
        }

        for payload in [agent_payload, policy_payload]:

            # add memory check
            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 200)

            # should fail since cpu check already exists
            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 400)

            # this should fail because both error and warning threshold are 0
            payload["error_threshold"] = 0
            payload["warning_threshold"] = 0

            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 400)

            # this should fail because error threshold is less than warning threshold
            payload["error_threshold"] = 20
            payload["warning_threshold"] = 30

            resp = self.client.post(url, payload, format="json")
            self.assertEqual(resp.status_code, 400)

        self.check_not_authenticated("post", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_run_checks(self, nats_cmd):
        agent = baker.make_recipe("agents.agent", version="1.4.1")
        agent_b4_141 = baker.make_recipe("agents.agent", version="1.4.0")

        url = f"{base_url}/{agent_b4_141.agent_id}/run/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_with({"func": "runchecks"}, wait=False)

        nats_cmd.reset_mock()
        nats_cmd.return_value = "busy"
        url = f"{base_url}/{agent.agent_id}/run/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
        nats_cmd.assert_called_with({"func": "runchecks"}, timeout=15)
        self.assertEqual(r.json(), f"Checks are already running on {agent.hostname}")

        nats_cmd.reset_mock()
        nats_cmd.return_value = "ok"
        url = f"{base_url}/{agent.agent_id}/run/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_with({"func": "runchecks"}, timeout=15)
        self.assertEqual(r.json(), f"Checks will now be re-run on {agent.hostname}")

        nats_cmd.reset_mock()
        nats_cmd.return_value = "timeout"
        url = f"{base_url}/{agent.agent_id}/run/"
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

        url = f"/checks/{check.id}/history/"

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

    def test_handle_eventlog_check(self):
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

        no_logs_data = {"id": eventlog.id, "log": []}

        # test failing when contains
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.alert_severity, "warning")
        self.assertEquals(new_check.status, "failing")

        # test passing when contains
        resp = self.client.patch(url, no_logs_data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "passing")

        # test failing when not contains and message and source
        eventlog.fail_when = "not_contains"
        eventlog.alert_severity = "error"
        eventlog.save()

        resp = self.client.patch(url, no_logs_data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "failing")
        self.assertEquals(new_check.alert_severity, "error")

        # test passing when contains with source and message
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        new_check = Check.objects.get(pk=eventlog.id)

        self.assertEquals(new_check.status, "passing")


class TestCheckPermissions(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.client_setup()

    def test_get_checks_permissions(self):
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        unauthorized_agent = baker.make_recipe("agents.agent")
        check = baker.make("checks.Check", agent=agent, _quantity=5)
        unauthorized_check = baker.make(
            "checks.Check", agent=unauthorized_agent, _quantity=7
        )

        policy_checks = baker.make("checks.Check", policy=policy, _quantity=2)

        # test super user access
        self.check_authorized_superuser("get", f"{base_url}/")
        self.check_authorized_superuser("get", f"/agents/{agent.agent_id}/checks/")
        self.check_authorized_superuser(
            "get", f"/agents/{unauthorized_agent.agent_id}/checks/"
        )
        self.check_authorized_superuser(
            "get", f"/automation/policies/{policy.id}/checks/"
        )

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)  # type: ignore

        self.check_not_authorized("get", f"{base_url}/")
        self.check_not_authorized("get", f"/agents/{agent.agent_id}/checks/")
        self.check_not_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/checks/"
        )
        self.check_not_authorized("get", f"/automation/policies/{policy.id}/checks/")

        # add list software role to user
        user.role.can_list_checks = True
        user.role.save()

        r = self.check_authorized("get", f"{base_url}/")
        self.assertEqual(len(r.data), 14)  # type: ignore
        r = self.check_authorized("get", f"/agents/{agent.agent_id}/checks/")
        self.assertEqual(len(r.data), 5)  # type: ignore
        r = self.check_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/checks/"
        )
        self.assertEqual(len(r.data), 7)  # type: ignore
        r = self.check_authorized("get", f"/automation/policies/{policy.id}/checks/")
        self.assertEqual(len(r.data), 2)  # type: ignore

        # test limiting to client
        user.role.can_view_clients.set([agent.client])
        self.check_not_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/checks/"
        )
        self.check_authorized("get", f"/agents/{agent.agent_id}/checks/")
        self.check_authorized("get", f"/automation/policies/{policy.id}/checks/")

        # make sure queryset is limited too
        r = self.client.get(f"{base_url}/")
        self.assertEqual(len(r.data), 7)  # type: ignore

    def test_add_check_permissions(self):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")

        policy_data = {
            "policy": policy.id,
            "check_type": "diskspace",
            "disk": "C:",
            "error_threshold": 55,
            "warning_threshold": 0,
            "fails_b4_alert": 3,
        }

        agent_data = {
            "agent": agent.agent_id,
            "check_type": "diskspace",
            "disk": "C:",
            "error_threshold": 55,
            "warning_threshold": 0,
            "fails_b4_alert": 3,
        }

        unauthorized_agent_data = {
            "agent": unauthorized_agent.agent_id,
            "check_type": "diskspace",
            "disk": "C:",
            "error_threshold": 55,
            "warning_threshold": 0,
            "fails_b4_alert": 3,
        }

        url = f"{base_url}/"

        for data in [policy_data, agent_data]:
            # test superuser access
            self.check_authorized_superuser("post", url, data)

            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)  # type: ignore

            # test user without role
            self.check_not_authorized("post", url, data)

            # add user to role and test
            setattr(user.role, "can_manage_checks", True)
            user.role.save()

            self.check_authorized("post", url, data)

            # limit user to client
            user.role.can_view_clients.set([agent.client])
            if "agent" in data.keys():
                self.check_authorized("post", url, data)
                self.check_not_authorized("post", url, unauthorized_agent_data)
            else:
                self.check_authorized("post", url, data)

    # mock the check delete method so it actually isn't deleted
    @patch("checks.models.Check.delete")
    def test_check_get_edit_delete_permissions(self, delete_check):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        check = baker.make("checks.Check", agent=agent)
        unauthorized_check = baker.make("checks.Check", agent=unauthorized_agent)
        policy_check = baker.make("checks.Check", policy=policy)

        for method in ["get", "put", "delete"]:

            url = f"{base_url}/{check.id}/"
            unauthorized_url = f"{base_url}/{unauthorized_check.id}/"
            policy_url = f"{base_url}/{policy_check.id}/"

            # test superuser access
            self.check_authorized_superuser(method, url)
            self.check_authorized_superuser(method, unauthorized_url)
            self.check_authorized_superuser(method, policy_url)

            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)  # type: ignore

            # test user without role
            self.check_not_authorized(method, url)
            self.check_not_authorized(method, unauthorized_url)
            self.check_not_authorized(method, policy_url)

            # add user to role and test
            setattr(
                user.role,
                "can_list_checks" if method == "get" else "can_manage_checks",
                True,
            )
            user.role.save()

            self.check_authorized(method, url)
            self.check_authorized(method, unauthorized_url)
            self.check_authorized(method, policy_url)

            # limit user to client if agent check
            user.role.can_view_clients.set([agent.client])

            self.check_authorized(method, url)
            self.check_not_authorized(method, unauthorized_url)
            self.check_authorized(method, policy_url)

    def test_check_action_permissions(self):

        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        check = baker.make("checks.Check", agent=agent)
        unauthorized_check = baker.make("checks.Check", agent=unauthorized_agent)

        for action in ["reset", "run"]:
            if action == "reset":
                url = f"{base_url}/{check.id}/{action}/"
                unauthorized_url = f"{base_url}/{unauthorized_check.id}/{action}/"
            else:
                url = f"{base_url}/{agent.agent_id}/{action}/"
                unauthorized_url = f"{base_url}/{unauthorized_agent.agent_id}/{action}/"

            # test superuser access
            self.check_authorized_superuser("post", url)
            self.check_authorized_superuser("post", unauthorized_url)

            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)  # type: ignore

            # test user without role
            self.check_not_authorized("post", url)
            self.check_not_authorized("post", unauthorized_url)

            # add user to role and test
            setattr(
                user.role,
                "can_manage_checks" if action == "reset" else "can_run_checks",
                True,
            )
            user.role.save()

            self.check_authorized("post", url)
            self.check_authorized("post", unauthorized_url)

            # limit user to client if agent check
            user.role.can_view_sites.set([agent.site])

            self.check_authorized("post", url)
            self.check_not_authorized("post", unauthorized_url)

    def test_check_history_permissions(self):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        check = baker.make("checks.Check", agent=agent)
        unauthorized_check = baker.make("checks.Check", agent=unauthorized_agent)

        url = f"{base_url}/{check.id}/history/"
        unauthorized_url = f"{base_url}/{unauthorized_check.id}/history/"

        # test superuser access
        self.check_authorized_superuser("patch", url)
        self.check_authorized_superuser("patch", unauthorized_url)

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)  # type: ignore

        # test user without role
        self.check_not_authorized("patch", url)
        self.check_not_authorized("patch", unauthorized_url)

        # add user to role and test
        setattr(
            user.role,
            "can_list_checks",
            True,
        )
        user.role.save()

        self.check_authorized("patch", url)
        self.check_authorized("patch", unauthorized_url)

        # limit user to client if agent check
        user.role.can_view_sites.set([agent.site])

        self.check_authorized("patch", url)
        self.check_not_authorized("patch", unauthorized_url)
