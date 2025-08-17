from unittest.mock import patch

from django.conf import settings
from django.utils import timezone as djangotime
from model_bakery import baker

from checks.models import CheckHistory, CheckResult
from tacticalrmm.constants import (
    AlertSeverity,
    CheckStatus,
    CheckType,
    EvtLogFailWhen,
    EvtLogTypes,
)
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
        self.assertEqual(len(resp.data), 8)

        # test checks agent url
        url = f"/agents/{agent.agent_id}/checks/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 4)

        # test agent doesn't exist
        url = "/agents/jh3498uf8fkh4ro8hfd8df98/checks/"
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
        self.assertEqual(resp.data, serializer.data)
        self.check_not_authenticated("get", url)

    def test_add_disk_check(self):
        # setup data
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")

        url = f"{base_url}/"

        agent_payload = {
            "agent": agent.agent_id,
            "check_type": CheckType.DISK_SPACE,
            "disk": "C:",
            "error_threshold": 55,
            "warning_threshold": 0,
            "fails_b4_alert": 3,
        }

        policy_payload = {
            "policy": policy.id,
            "check_type": CheckType.DISK_SPACE,
            "disk": "C:",
            "error_threshold": 55,
            "warning_threshold": 0,
            "fails_b4_alert": 3,
        }

        for payload in (agent_payload, policy_payload):
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
            "check_type": CheckType.CPU_LOAD,
            "error_threshold": 66,
            "warning_threshold": 0,
            "fails_b4_alert": 9,
        }

        policy_payload = {
            "policy": policy.id,
            "check_type": CheckType.CPU_LOAD,
            "error_threshold": 66,
            "warning_threshold": 0,
            "fails_b4_alert": 9,
        }

        for payload in (agent_payload, policy_payload):
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

    def test_reset_all_checks_status(self):
        # setup data
        agent = baker.make_recipe("agents.agent")
        check = baker.make_recipe("checks.diskspace_check", agent=agent)
        baker.make("checks.CheckResult", assigned_check=check, agent=agent)
        baker.make(
            "checks.CheckHistory",
            check_id=check.id,
            agent_id=agent.agent_id,
            _quantity=30,
        )
        baker.make(
            "checks.CheckHistory",
            check_id=check.id,
            agent_id=agent.agent_id,
            _quantity=30,
        )

        url = f"{base_url}/{agent.agent_id}/resetall/"

        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

        self.check_not_authenticated("post", url)

    def test_add_memory_check(self):
        url = f"{base_url}/"
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")

        agent_payload = {
            "agent": agent.agent_id,
            "check_type": CheckType.MEMORY,
            "error_threshold": 78,
            "warning_threshold": 0,
            "fails_b4_alert": 1,
        }

        policy_payload = {
            "policy": policy.id,
            "check_type": CheckType.MEMORY,
            "error_threshold": 78,
            "warning_threshold": 0,
            "fails_b4_alert": 1,
        }

        for payload in (agent_payload, policy_payload):
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
        agent = baker.make_recipe("agents.agent", version=settings.LATEST_AGENT_VER)

        nats_cmd.reset_mock()
        nats_cmd.return_value = "busy"
        url = f"{base_url}/{agent.agent_id}/run/"
        r = self.client.post(url)
        self.assertEqual(r.status_code, 400)
        nats_cmd.assert_called_with({"func": "runchecks"}, timeout=15)
        self.assertEqual(r.json(), f"Checks are already running on {agent.hostname}")

        nats_cmd.reset_mock()
        nats_cmd.return_value = "ok"
        url = f"{base_url}/{agent.agent_id}/run/"
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        nats_cmd.assert_called_with({"func": "runchecks"}, timeout=15)

        nats_cmd.reset_mock()
        nats_cmd.return_value = "timeout"
        url = f"{base_url}/{agent.agent_id}/run/"
        r = self.client.post(url)
        self.assertEqual(r.status_code, 400)
        nats_cmd.assert_called_with({"func": "runchecks"}, timeout=15)
        self.assertEqual(r.json(), "Unable to contact the agent")

        self.check_not_authenticated("post", url)

    def test_get_check_history(self):
        # setup data
        agent = baker.make_recipe("agents.agent")
        check = baker.make_recipe("checks.diskspace_check", agent=agent)
        check_result = baker.make(
            "checks.CheckResult", assigned_check=check, agent=agent
        )
        baker.make(
            "checks.CheckHistory",
            check_id=check.id,
            agent_id=agent.agent_id,
            _quantity=30,
        )
        check_history_data = baker.make(
            "checks.CheckHistory",
            check_id=check.id,
            agent_id=agent.agent_id,
            _quantity=30,
        )

        # need to manually set the date back 35 days
        for check_history in check_history_data:
            check_history.x = djangotime.now() - djangotime.timedelta(days=35)
            check_history.save()

        # test invalid check pk
        resp = self.client.patch("/checks/500/history/", format="json")
        self.assertEqual(resp.status_code, 404)

        url = f"/checks/{check_result.id}/history/"

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
        for check_history in check_history_data:
            check_history.x = djangotime.now() - djangotime.timedelta(days=35)
            check_history.save()

        # prune data 30 days old
        prune_check_history(30)
        self.assertEqual(CheckHistory.objects.count(), 30)

        # prune all Check history Data
        prune_check_history(0)
        self.assertEqual(CheckHistory.objects.count(), 0)

    def test_handle_script_check(self):
        url = "/api/v3/checkrunner/"

        check = baker.make_recipe("checks.script_check", agent=self.agent)

        # test failing
        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "retcode": 500,
            "stderr": "error",
            "stdout": "message",
            "runtime": 5.000,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.ERROR)

        # test passing
        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "retcode": 0,
            "stderr": "error",
            "stdout": "message",
            "runtime": 5.000,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.PASSING)

        # test failing info
        check.info_return_codes = [20, 30, 50]
        check.save()

        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "retcode": 30,
            "stderr": "error",
            "stdout": "message",
            "runtime": 5.000,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.INFO)

        # test failing warning
        check.warning_return_codes = [80, 100, 1040]
        check.save()

        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "retcode": 1040,
            "stderr": "error",
            "stdout": "message",
            "runtime": 5.000,
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.WARNING)

    def test_handle_diskspace_check(self):
        url = "/api/v3/checkrunner/"

        check = baker.make_recipe(
            "checks.diskspace_check",
            warning_threshold=20,
            error_threshold=10,
            agent=self.agent,
        )

        # test warning threshold failure
        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "exists": True,
            "percent_used": 85,
            "total": 500,
            "free": 400,
            "more_info": "More info",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.WARNING)

        # test error failure
        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "exists": True,
            "percent_used": 95,
            "total": 500,
            "free": 400,
            "more_info": "More info",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.ERROR)

        # test disk not exist
        data = {"id": check.id, "agent_id": self.agent.agent_id, "exists": False}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.ERROR)

        # test warning threshold 0
        check.warning_threshold = 0
        check.save()

        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "exists": True,
            "percent_used": 95,
            "total": 500,
            "free": 400,
            "more_info": "More info",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.ERROR)

        # test error threshold 0
        check.warning_threshold = 50
        check.error_threshold = 0
        check.save()
        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "exists": True,
            "percent_used": 95,
            "total": 500,
            "free": 400,
            "more_info": "More info",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.WARNING)

        # test passing
        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "exists": True,
            "percent_used": 50,
            "total": 500,
            "free": 400,
            "more_info": "More info",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.PASSING)

    def test_handle_cpuload_check(self):
        url = "/api/v3/checkrunner/"

        check = baker.make_recipe(
            "checks.cpuload_check",
            warning_threshold=70,
            error_threshold=90,
            agent=self.agent,
        )

        # test failing warning
        data = {"id": check.id, "agent_id": self.agent.agent_id, "percent": 80}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.WARNING)

        # test failing error
        data = {"id": check.id, "agent_id": self.agent.agent_id, "percent": 95}

        # reset check history
        check_result.history = []
        check_result.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.ERROR)

        # test passing
        data = {"id": check.id, "agent_id": self.agent.agent_id, "percent": 50}

        # reset check history
        check_result.history = []
        check_result.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.PASSING)

        # test warning threshold 0
        check.warning_threshold = 0
        check.save()
        data = {"id": check.id, "agent_id": self.agent.agent_id, "percent": 95}

        # reset check history
        check_result.history = []
        check_result.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.ERROR)

        # test error threshold 0
        check.warning_threshold = 50
        check.error_threshold = 0
        check.save()
        data = {"id": check.id, "agent_id": self.agent.agent_id, "percent": 95}

        # reset check history
        check_result.history = []
        check_result.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.WARNING)

    def test_handle_memory_check(self):
        url = "/api/v3/checkrunner/"

        check = baker.make_recipe(
            "checks.memory_check",
            warning_threshold=70,
            error_threshold=90,
            agent=self.agent,
        )

        # test failing warning
        data = {"id": check.id, "agent_id": self.agent.agent_id, "percent": 80}

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.WARNING)

        # test failing error
        data = {"id": check.id, "agent_id": self.agent.agent_id, "percent": 95}

        # reset check history
        check_result.history = []
        check_result.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.ERROR)

        # test passing
        data = {"id": check.id, "agent_id": self.agent.agent_id, "percent": 50}

        # reset check history
        check_result.history = []
        check_result.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.PASSING)

        # test warning threshold 0
        check.warning_threshold = 0
        check.save()
        data = {"id": check.id, "agent_id": self.agent.agent_id, "percent": 95}

        # reset check history
        check_result.history = []
        check_result.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.ERROR)

        # test error threshold 0
        check.warning_threshold = 50
        check.error_threshold = 0
        check.save()
        data = {"id": check.id, "agent_id": self.agent.agent_id, "percent": 95}

        # reset check history
        check_result.history = []
        check_result.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check_result.alert_severity, AlertSeverity.WARNING)

    def test_handle_ping_check(self):
        url = "/api/v3/checkrunner/"

        check = baker.make_recipe(
            "checks.ping_check", agent=self.agent, alert_severity=AlertSeverity.INFO
        )

        # test failing info
        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "status": CheckStatus.FAILING,
            "output": "reply from a.com",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check.alert_severity, AlertSeverity.INFO)

        # test failing warning
        check.alert_severity = AlertSeverity.WARNING
        check.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check.alert_severity, AlertSeverity.WARNING)

        # test failing error
        check.alert_severity = AlertSeverity.ERROR
        check.save()

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check.alert_severity, AlertSeverity.ERROR)

        # test failing error
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check.alert_severity, AlertSeverity.ERROR)

        # test passing
        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "status": CheckStatus.PASSING,
            "output": "reply from a.com",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.PASSING)

    @patch("agents.models.Agent.nats_cmd")
    def test_handle_winsvc_check(self, nats_cmd):
        url = "/api/v3/checkrunner/"

        check = baker.make_recipe(
            "checks.winsvc_check", agent=self.agent, alert_severity=AlertSeverity.INFO
        )

        # test passing running
        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "status": CheckStatus.PASSING,
            "more_info": "ok",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.PASSING)

        # test failing
        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
            "status": CheckStatus.FAILING,
            "more_info": "ok",
        }

        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)
        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check.alert_severity, AlertSeverity.INFO)

    def test_handle_eventlog_check(self):
        url = "/api/v3/checkrunner/"

        check = baker.make_recipe(
            "checks.eventlog_check",
            event_type=EvtLogTypes.WARNING,
            fail_when=EvtLogFailWhen.CONTAINS,
            event_id=123,
            alert_severity=AlertSeverity.WARNING,
            agent=self.agent,
        )

        data = {
            "id": check.id,
            "agent_id": self.agent.agent_id,
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

        no_logs_data = {"id": check.id, "agent_id": self.agent.agent_id, "log": []}

        # test failing when contains
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check.alert_severity, AlertSeverity.WARNING)
        self.assertEqual(check_result.status, CheckStatus.FAILING)

        # test passing when contains
        resp = self.client.patch(url, no_logs_data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.PASSING)

        # test failing when not contains and message and source
        check.fail_when = EvtLogFailWhen.NOT_CONTAINS
        check.alert_severity = AlertSeverity.ERROR
        check.save()

        resp = self.client.patch(url, no_logs_data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.FAILING)
        self.assertEqual(check.alert_severity, AlertSeverity.ERROR)

        # test passing when contains with source and message
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)

        check_result = CheckResult.objects.get(assigned_check=check, agent=self.agent)

        self.assertEqual(check_result.status, CheckStatus.PASSING)


class TestCheckPermissions(TacticalTestCase):
    def setUp(self):
        self.setup_coresettings()
        self.setup_client()

    def test_get_checks_permissions(self):
        agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")
        unauthorized_agent = baker.make_recipe("agents.agent")
        check = baker.make("checks.Check", agent=agent, _quantity=5)  # noqa
        unauthorized_check = baker.make(  # noqa
            "checks.Check", agent=unauthorized_agent, _quantity=7
        )

        policy_checks = baker.make("checks.Check", policy=policy, _quantity=2)  # noqa

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
        self.client.force_authenticate(user=user)

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
        self.assertEqual(len(r.data), 14)
        r = self.check_authorized("get", f"/agents/{agent.agent_id}/checks/")
        self.assertEqual(len(r.data), 5)
        r = self.check_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/checks/"
        )
        self.assertEqual(len(r.data), 7)
        r = self.check_authorized("get", f"/automation/policies/{policy.id}/checks/")
        self.assertEqual(len(r.data), 2)

        # test limiting to client
        user.role.can_view_clients.set([agent.client])
        self.check_not_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/checks/"
        )
        self.check_authorized("get", f"/agents/{agent.agent_id}/checks/")
        self.check_authorized("get", f"/automation/policies/{policy.id}/checks/")

        # make sure queryset is limited too
        r = self.client.get(f"{base_url}/")
        self.assertEqual(len(r.data), 7)

    def test_add_check_permissions(self):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        policy = baker.make("automation.Policy")

        policy_data = {
            "policy": policy.id,
            "check_type": CheckType.DISK_SPACE,
            "disk": "C:",
            "error_threshold": 55,
            "warning_threshold": 0,
            "fails_b4_alert": 3,
        }

        agent_data = {
            "agent": agent.agent_id,
            "check_type": CheckType.DISK_SPACE,
            "disk": "C:",
            "error_threshold": 55,
            "warning_threshold": 0,
            "fails_b4_alert": 3,
        }

        unauthorized_agent_data = {
            "agent": unauthorized_agent.agent_id,
            "check_type": CheckType.DISK_SPACE,
            "disk": "C:",
            "error_threshold": 55,
            "warning_threshold": 0,
            "fails_b4_alert": 3,
        }

        url = f"{base_url}/"

        for data in (policy_data, agent_data):
            # test superuser access
            self.check_authorized_superuser("post", url, data)

            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)

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

        for method in ("get", "put", "delete"):
            url = f"{base_url}/{check.id}/"
            unauthorized_url = f"{base_url}/{unauthorized_check.id}/"
            policy_url = f"{base_url}/{policy_check.id}/"

            # test superuser access
            self.check_authorized_superuser(method, url)
            self.check_authorized_superuser(method, unauthorized_url)
            self.check_authorized_superuser(method, policy_url)

            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)

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

    @patch("agents.models.Agent.nats_cmd")
    def test_check_action_permissions(self, nats_cmd):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        check = baker.make("checks.Check", agent=agent)
        check_result = baker.make(
            "checks.CheckResult", agent=agent, assigned_check=check
        )
        unauthorized_check = baker.make("checks.Check", agent=unauthorized_agent)
        unauthorized_check_result = baker.make(
            "checks.CheckResult",
            agent=unauthorized_agent,
            assigned_check=unauthorized_check,
        )

        for action in ("reset", "run"):
            if action == "reset":
                url = f"{base_url}/{check_result.id}/{action}/"
                unauthorized_url = (
                    f"{base_url}/{unauthorized_check_result.id}/{action}/"
                )
            else:
                url = f"{base_url}/{agent.agent_id}/{action}/"
                unauthorized_url = f"{base_url}/{unauthorized_agent.agent_id}/{action}/"

            # test superuser access
            self.check_authorized_superuser("post", url)
            self.check_authorized_superuser("post", unauthorized_url)

            user = self.create_user_with_roles([])
            self.client.force_authenticate(user=user)

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
        check_result = baker.make(
            "checks.CheckResult", agent=agent, assigned_check=check
        )
        unauthorized_check = baker.make("checks.Check", agent=unauthorized_agent)
        unauthorized_check_result = baker.make(
            "checks.CheckResult",
            agent=unauthorized_agent,
            assigned_check=unauthorized_check,
        )

        url = f"{base_url}/{check_result.id}/history/"
        unauthorized_url = f"{base_url}/{unauthorized_check_result.id}/history/"

        # test superuser access
        self.check_authorized_superuser("patch", url)
        self.check_authorized_superuser("patch", unauthorized_url)

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

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
