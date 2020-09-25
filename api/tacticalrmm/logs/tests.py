from tacticalrmm.test import PlainTestCase
from logs.models import AuditLog
from django.utils import timezone as djangotime


class TestAuditViews(PlainTestCase):

    def setUp(self):
        self.authenticate()
        self.setup_coresettings()

    def create_audit_records(self):
        # create new records
        AuditLog.audit_mesh_session("jim", "AgentHostname1")
        AuditLog.audit_raw_command("jim", "AgentHostname2", "whoami", "batch")
        AuditLog.audit_object_changed("jim", "policy", {}, {}, "Policy Name")
        AuditLog.audit_object_add("jim", "policy", {}, "Another Policy")
        AuditLog.audit_object_delete("jim", "policy", {}, "Another Policy")
        AuditLog.audit_object_delete("james", "agent", {}, "AgentHostname1")
        AuditLog.audit_script_run("james", "AgentHostname2", "Script Name")
        AuditLog.audit_user_failed_login("james")
        AuditLog.audit_user_failed_twofactor("james")
        AuditLog.audit_user_login_successful("jim")

        # create some old records
        log1 = AuditLog.objects.create(
            username="james", 
            agent="AgentHostname1", 
            action="execute_command",
            object_type="agent",
            message="jim issued powershell command on AgentHostname"
        )
        log2 = AuditLog.objects.create(
            username="jim",
            action="login",
            object_type="user",
            message="jim logged in successfully"
        )
        log3 = AuditLog.objects.create(
            username="jim",
            agent="AgentHostname2",
            action="execute_script",
            object_type="agent",
            message='jim ran script: "Script Name" on AgentHostname'
        )
        log4 = AuditLog.objects.create(
            username="james",
            agent="AgentHostname1",
            action="execute_command",
            object_type="agent",
            message="jim issued powershell command on AgentHostname"
        )

        log1.entry_time = djangotime.now() - djangotime.timedelta(days=15)
        log1.save()
        log2.entry_time = djangotime.now() - djangotime.timedelta(days=31)
        log2.save()
        log3.entry_time = djangotime.now() - djangotime.timedelta(days=130)
        log3.save()
        log4.entry_time = djangotime.now() - djangotime.timedelta(days=365)
        log4.save()

    def test_get_audit_logs(self):
        url = "/logs/auditlogs/"

        # create data
        self.create_audit_records()
        
        # test data and result counts
        data = [
            {
                "filter": {"timeFilter": 30}, "count": 11
            },
            {
                "filter": {"timeFilter": 45, "agentFilter": ["AgentHostname2"]}, "count": 2
            },
            {
                "filter": {"userFilter": ["jim"], "agentFilter": ["AgentHostname1"]}, "count": 1
            },
            {
                "filter": {"timeFilter": 180, "userFilter": ["james"], "agentFilter": ["AgentHostname1"]}, "count": 1
            },
            {
                "filter": {}, "count": 14
            },
            {
                "filter": {"agentFilter": ["DoesntExist"]}, "count": 0
            },
            {
                "filter": {"timeFilter": 35, "userFilter": ["james", "jim"], "agentFilter": ["AgentHostname1", "AgentHostname2"]}, "count": 4
            },
            {
                "filter": {"timeFilter": 35, "userFilter": ["james", "jim"]}, "count": 12
            },
        ]

        for req in data:

            resp = self.client.patch(url, req["filter"], format="json")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(resp.data), req["count"])


        self.check_not_authenticated("patch", url)

