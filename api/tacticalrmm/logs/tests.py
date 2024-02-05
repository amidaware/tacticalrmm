from itertools import cycle
from unittest.mock import patch

from django.utils import timezone as djangotime
from model_bakery import baker, seq

from tacticalrmm.constants import DebugLogLevel, DebugLogType, PAAction, PAStatus
from tacticalrmm.test import TacticalTestCase

base_url = "/logs"


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
                (
                    pagination["rowsPerPage"]
                    if req["count"] > pagination["rowsPerPage"]
                    else req["count"]
                ),
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
            action_type=PAAction.CHOCO_INSTALL,
            details={"name": "googlechrome", "output": None, "installed": False},
            _quantity=12,
        )
        baker.make(
            "logs.PendingAction",
            agent=agent2,
            action_type=PAAction.CHOCO_INSTALL,
            status=PAStatus.COMPLETED,
            details={"name": "adobereader", "output": None, "installed": False},
            _quantity=14,
        )

        r = self.client.get(url, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 26)

        self.check_not_authenticated("get", url)

    @patch("agents.models.Agent.nats_cmd")
    def test_cancel_pending_action(self, nats_cmd):
        nats_cmd.return_value = "ok"
        agent = baker.make_recipe("agents.online_agent")
        action = baker.make(
            "logs.PendingAction",
            agent=agent,
            action_type=PAAction.SCHED_REBOOT,
            details={
                "time": "2021-01-13 18:20:00",
                "taskname": "TacticalRMM_SchedReboot_wYzCCDVXlc",
            },
        )

        url = f"{base_url}/pendingactions/{action.id}/"

        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 200)
        nats_data = {
            "func": "delschedtask",
            "schedtaskpayload": {"name": "TacticalRMM_SchedReboot_wYzCCDVXlc"},
        }
        nats_cmd.assert_called_with(nats_data, timeout=10)

        # try request again and it should 404 since pending action doesn't exist
        r = self.client.delete(url, format="json")
        self.assertEqual(r.status_code, 404)

        nats_cmd.reset_mock()

        action2 = baker.make(
            "logs.PendingAction",
            agent=agent,
            action_type=PAAction.SCHED_REBOOT,
            details={
                "time": "2021-01-13 18:20:00",
                "taskname": "TacticalRMM_SchedReboot_wYzCCDVXlc",
            },
        )

        nats_cmd.return_value = "error deleting sched task"
        r = self.client.delete(
            f"{base_url}/pendingactions/{action2.id}/", format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, "error deleting sched task")

        self.check_not_authenticated("delete", url)

    def test_get_debug_log(self):
        url = "/logs/debug/"

        # create data
        agent = baker.make_recipe("agents.agent")
        baker.make(
            "logs.DebugLog",
            log_level=cycle([i.value for i in DebugLogLevel]),
            log_type=DebugLogType.AGENT_ISSUES,
            agent=agent,
            _quantity=4,
        )

        logs = baker.make(  # noqa
            "logs.DebugLog",
            log_type=DebugLogType.SYSTEM_ISSUES,
            log_level=cycle([i.value for i in DebugLogLevel]),
            _quantity=15,
        )

        # test agent filter
        data = {"agentFilter": agent.agent_id}
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 4)

        # test log type filter and agent
        data = {"agentFilter": agent.agent_id, "logLevelFilter": "warning"}
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

        # test time filter with other
        data = {
            "logTypeFilter": DebugLogType.SYSTEM_ISSUES.value,
            "logLevelFilter": "error",
        }
        resp = self.client.patch(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 4)

        self.check_not_authenticated("patch", url)

    def test_auditlog_permissions(self):
        site = self.create_audit_records()["site"]

        url = f"{base_url}/audit/"

        data = {
            "pagination": {
                "rowsPerPage": 100,
                "page": 1,
                "sortBy": "entry_time",
                "descending": True,
            }
        }

        # test superuser access
        self.check_authorized_superuser("patch", url, data)

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        # test user without role
        self.check_not_authorized("patch", url, data)

        # add user to role and test
        user.role.can_view_auditlogs = True
        user.role.save()

        response = self.check_authorized("patch", url, data)
        self.assertEqual(len(response.data["audit_logs"]), 86)

        # limit user to client if agent check
        user.role.can_view_sites.set([site])

        response = self.check_authorized("patch", url, data)
        self.assertEqual(len(response.data["audit_logs"]), 63)

        # limit user to client if agent check
        user.role.can_view_clients.set([site.client])
        response = self.check_authorized("patch", url, data)
        self.assertEqual(len(response.data["audit_logs"]), 63)

    def test_debuglog_permissions(self):
        # create data
        agent = baker.make_recipe("agents.agent")
        agent2 = baker.make_recipe("agents.agent")
        baker.make(
            "logs.DebugLog",
            log_level=cycle([i.value for i in DebugLogLevel]),
            log_type=DebugLogType.AGENT_ISSUES,
            agent=agent,
            _quantity=4,
        )

        baker.make(
            "logs.DebugLog",
            log_level=cycle([i.value for i in DebugLogLevel]),
            log_type=DebugLogType.AGENT_ISSUES,
            agent=agent2,
            _quantity=8,
        )

        baker.make(
            "logs.DebugLog",
            log_type=DebugLogType.SYSTEM_ISSUES,
            log_level=cycle([i.value for i in DebugLogLevel]),
            _quantity=15,
        )

        url = f"{base_url}/debug/"

        # test superuser access
        self.check_authorized_superuser(
            "patch",
            url,
        )

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        # test user without role
        self.check_not_authorized("patch", url)

        # add user to role and test
        user.role.can_view_debuglogs = True
        user.role.save()

        response = self.check_authorized("patch", url)
        self.assertEqual(len(response.data), 27)

        # limit user to site
        user.role.can_view_sites.set([agent.site])

        response = self.check_authorized("patch", url)
        self.assertEqual(len(response.data), 19)

        # limit user to client
        user.role.can_view_sites.clear()
        user.role.can_view_clients.set([agent2.site.client])
        response = self.check_authorized("patch", url)
        self.assertEqual(len(response.data), 23)

        # limit user to client and site
        user.role.can_view_sites.set([agent.site])
        user.role.can_view_clients.set([agent2.site.client])
        response = self.check_authorized("patch", url)
        self.assertEqual(len(response.data), 27)

    def test_get_pendingaction_permissions(self):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        actions = baker.make("logs.PendingAction", agent=agent, _quantity=5)  # noqa
        unauthorized_actions = baker.make(  # noqa
            "logs.PendingAction", agent=unauthorized_agent, _quantity=7
        )

        # test super user access
        self.check_authorized_superuser("get", f"{base_url}/pendingactions/")
        self.check_authorized_superuser(
            "get", f"/agents/{agent.agent_id}/pendingactions/"
        )
        self.check_authorized_superuser(
            "get", f"/agents/{unauthorized_agent.agent_id}/pendingactions/"
        )

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        self.check_not_authorized("get", f"{base_url}/pendingactions/")
        self.check_not_authorized("get", f"/agents/{agent.agent_id}/pendingactions/")
        self.check_not_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/pendingactions/"
        )

        # add list software role to user
        user.role.can_list_pendingactions = True
        user.role.save()

        r = self.check_authorized("get", f"{base_url}/pendingactions/")
        self.assertEqual(len(r.data), 12)
        r = self.check_authorized("get", f"/agents/{agent.agent_id}/pendingactions/")
        self.assertEqual(len(r.data), 5)
        r = self.check_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/pendingactions/"
        )
        self.assertEqual(len(r.data), 7)

        # test limiting to client
        user.role.can_view_clients.set([agent.client])
        self.check_not_authorized(
            "get", f"/agents/{unauthorized_agent.agent_id}/pendingactions/"
        )
        self.check_authorized("get", f"/agents/{agent.agent_id}/pendingactions/")

        # make sure queryset is limited too
        r = self.client.get(f"{base_url}/pendingactions/")
        self.assertEqual(len(r.data), 5)

    @patch("agents.models.Agent.nats_cmd", return_value="ok")
    @patch("logs.models.PendingAction.delete")
    def test_delete_pendingaction_permissions(self, delete, nats_cmd):
        agent = baker.make_recipe("agents.agent")
        unauthorized_agent = baker.make_recipe("agents.agent")
        action = baker.make(
            "logs.PendingAction", agent=agent, details={"taskname": "Task"}
        )
        unauthorized_action = baker.make(
            "logs.PendingAction", agent=unauthorized_agent, details={"taskname": "Task"}
        )

        url = f"{base_url}/pendingactions/{action.id}/"
        unauthorized_url = f"{base_url}/pendingactions/{unauthorized_action.id}/"

        # test superuser access
        self.check_authorized_superuser("delete", url)
        self.check_authorized_superuser("delete", unauthorized_url)

        user = self.create_user_with_roles([])
        self.client.force_authenticate(user=user)

        # test user without role
        self.check_not_authorized("delete", url)
        self.check_not_authorized("delete", unauthorized_url)

        # add user to role and test
        user.role.can_manage_pendingactions = True
        user.role.save()

        self.check_authorized("delete", url)
        self.check_authorized("delete", unauthorized_url)

        # limit user to site
        user.role.can_view_sites.set([agent.site])

        self.check_authorized("delete", url)
        self.check_not_authorized("delete", unauthorized_url)


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
