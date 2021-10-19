from itertools import cycle
from unittest.mock import patch

from django.utils import timezone as djangotime
from model_bakery import baker, seq
from tacticalrmm.test import TacticalTestCase

from logs.models import PendingAction


class TestAuditViews(TacticalTestCase):
    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def create_audit_records(self):

        # create clients for client filter
        site = baker.make("clients.Site")
        agent1 = baker.make_recipe("agents.agent", site=site, hostname="AgentHostname1")
        agent2 = baker.make_recipe("agents.agent", hostname="AgentHostname2")
        agent0 = baker.make_recipe("agents.agent", hostname="AgentHostname")

        # user jim agent logs
        baker.make_recipe(
            "logs.agent_logs",
            username="jim",
            agent="AgentHostname1",
            agent_id=agent1.agent_id,
            _quantity=15,
        )
        baker.make_recipe(
            "logs.agent_logs",
            username="jim",
            agent="AgentHostname2",
            agent_id=agent2.agent_id,
            _quantity=8,
        )

        # user james agent logs
        baker.make_recipe(
            "logs.agent_logs",
            username="james",
            agent="AgentHostname1",
            agent_id=agent1.agent_id,
            _quantity=7,
        )
        baker.make_recipe(
            "logs.agent_logs",
            username="james",
            agent="AgentHostname2",
            agent_id=agent2.agent_id,
            _quantity=10,
        )

        # generate agent logs with random usernames
        baker.make_recipe(
            "logs.agent_logs",
            agent=seq("AgentHostname"),
            agent_id=seq(agent1.agent_id),
            _quantity=5,
        )

        # generate random object data
        baker.make_recipe(
            "logs.object_logs",
            username="james",
            _quantity=17,
        )

        # generate login data for james
        baker.make_recipe(
            "logs.login_logs",
            username="james",
            _quantity=11,
        )

        # generate login data for jim
        baker.make_recipe(
            "logs.login_logs",
            username="jim",
            _quantity=13,
        )

        return {"site": site, "agents": [agent0, agent1, agent2]}

    def test_get_audit_logs(self):
        url = "/logs/audit/"

        # create data
        data = self.create_audit_records()

        # test data and result counts
        data = [
            {"filter": {"timeFilter": 30}, "count": 86},
            {
                "filter": {
                    "timeFilter": 45,
                    "agentFilter": [data["agents"][2].agent_id],
                },
                "count": 18,
            },
            {
                "filter": {
                    "userFilter": ["jim"],
                    "agentFilter": [data["agents"][1].agent_id],
                },
                "count": 15,
            },
            {
                "filter": {
                    "timeFilter": 180,
                    "userFilter": ["james"],
                    "agentFilter": [data["agents"][1].agent_id],
                },
                "count": 7,
            },
            {"filter": {}, "count": 86},
            {"filter": {"agentFilter": [500]}, "count": 0},
            {
                "filter": {
                    "timeFilter": 35,
                    "userFilter": ["james", "jim"],
                    "agentFilter": [
                        data["agents"][1].agent_id,
                        data["agents"][2].agent_id,
                    ],
                },
                "count": 40,
            },
            {"filter": {"timeFilter": 35, "userFilter": ["james", "jim"]}, "count": 81},
            {"filter": {"objectFilter": ["user"]}, "count": 26},
            {"filter": {"actionFilter": ["login"]}, "count": 12},
            {
                "filter": {"clientFilter": [data["site"].client.id]},
                "count": 22,
            },
        ]

        pagination = {
            "rowsPerPage": 25,
            "page": 1,
            "sortBy": "entry_time",
            "descending": True,
        }

        for req in data:
            resp = self.client.patch(
                url, {**req["filter"], "pagination": pagination}, format="json"
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(
                len(resp.data["audit_logs"]),  # type:ignore
                pagination["rowsPerPage"]
                if req["count"] > pagination["rowsPerPage"]
                else req["count"],
            )
            self.assertEqual(resp.data["total"], req["count"])  # type:ignore

        self.check_not_authenticated("patch", url)

    def test_get_pending_actions(self):
        url = "/logs/pendingactions/"
        agent1 = baker.make_recipe("agents.online_agent")
        agent2 = baker.make_recipe("agents.online_agent")

        baker.make(
            "logs.PendingAction",
            agent=agent1,
            action_type="chocoinstall",
            details={"name": "googlechrome", "output": None, "installed": False},
            _quantity=12,
        )
        baker.make(
            "logs.PendingAction",
            agent=agent2,
            action_type="chocoinstall",
            status="completed",
            details={"name": "adobereader", "output": None, "installed": False},
            _quantity=14,
        )

        data = {"showCompleted": False}
        r = self.client.patch(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["actions"]), 12)  # type: ignore
        self.assertEqual(r.data["completed_count"], 14)  # type: ignore
        self.assertEqual(r.data["total"], 26)  # type: ignore

        PendingAction.objects.filter(action_type="chocoinstall").update(
            status="completed"
        )
        data = {"showCompleted": True}
        r = self.client.patch(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["actions"]), 26)  # type: ignore
        self.assertEqual(r.data["completed_count"], 26)  # type: ignore
        self.assertEqual(r.data["total"], 26)  # type: ignore

        data = {"showCompleted": True, "agentPK": agent1.pk}
        r = self.client.patch(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["actions"]), 12)  # type: ignore
        self.assertEqual(r.data["completed_count"], 12)  # type: ignore
        self.assertEqual(r.data["total"], 12)  # type: ignore

        self.check_not_authenticated("patch", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_cancel_pending_action(self, nats_cmd):
        nats_cmd.return_value = "ok"
        url = "/logs/pendingactions/"
        agent = baker.make_recipe("agents.online_agent")
        action = baker.make(
            "logs.PendingAction",
            agent=agent,
            action_type="schedreboot",
            details={
                "time": "2021-01-13 18:20:00",
                "taskname": "TacticalRMM_SchedReboot_wYzCCDVXlc",
            },
        )

        data = {"pk": action.pk}  # type: ignore
        r = self.client.delete(url, data, format="json")
        self.assertEqual(r.status_code, 200)
        nats_data = {
            "func": "delschedtask",
            "schedtaskpayload": {"name": "TacticalRMM_SchedReboot_wYzCCDVXlc"},
        }
        nats_cmd.assert_called_with(nats_data, timeout=10)

        # try request again and it should 404 since pending action doesn't exist
        r = self.client.delete(url, data, format="json")
        self.assertEqual(r.status_code, 404)

        nats_cmd.reset_mock()

        action2 = baker.make(
            "logs.PendingAction",
            agent=agent,
            action_type="schedreboot",
            details={
                "time": "2021-01-13 18:20:00",
                "taskname": "TacticalRMM_SchedReboot_wYzCCDVXlc",
            },
        )

        data = {"pk": action2.pk}  # type: ignore
        nats_cmd.return_value = "error deleting sched task"
        r = self.client.delete(url, data, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, "error deleting sched task")  # type: ignore

        self.check_not_authenticated("delete", url)

    def test_get_debug_log(self):
        url = "/logs/debug/"

        # create data
        agent = baker.make_recipe("agents.agent")
        baker.make(
            "logs.DebugLog",
            log_level=cycle(["error", "info", "warning", "critical"]),
            log_type="agent_issues",
            agent=agent,
            _quantity=4,
        )

        logs = baker.make(
            "logs.DebugLog",
            log_type="system_issues",
            log_level=cycle(["error", "info", "warning", "critical"]),
            _quantity=15,
        )

        # test agent filter
        data = {"agentFilter": agent.agent_id}
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 4)  # type: ignore

        # test log type filter and agent
        data = {"agentFilter": agent.agent_id, "logLevelFilter": "warning"}
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)  # type: ignore

        # test time filter with other
        data = {"logTypeFilter": "system_issues", "logLevelFilter": "error"}
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 4)  # type: ignore

        self.check_not_authenticated("patch", url)


class TestLogTasks(TacticalTestCase):
    def test_prune_debug_log(self):
        from .models import DebugLog
        from .tasks import prune_debug_log

        # setup data
        debug_log = baker.make(
            "logs.DebugLog",
            _quantity=50,
        )

        days = 0
        for item in debug_log:  # type:ignore
            item.entry_time = djangotime.now() - djangotime.timedelta(days=days)
            item.save()
            days = days + 5

        # delete AgentHistory older than 30 days
        prune_debug_log(30)

        self.assertEqual(DebugLog.objects.count(), 6)

    def test_prune_audit_log(self):
        from .models import AuditLog
        from .tasks import prune_audit_log

        # setup data
        audit_log = baker.make(
            "logs.AuditLog",
            _quantity=50,
        )

        days = 0
        for item in audit_log:  # type:ignore
            item.entry_time = djangotime.now() - djangotime.timedelta(days=days)
            item.save()
            days = days + 5

        # delete AgentHistory older than 30 days
        prune_audit_log(30)

        self.assertEqual(AuditLog.objects.count(), 6)
