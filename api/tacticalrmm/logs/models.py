import datetime as dt
from django.db import models
from django.utils import timezone
from agents.models import Agent

ACTION_TYPE_CHOICES = [
    ("schedreboot", "Scheduled Reboot"),
    ("taskaction", "Scheduled Task Action"),
]

AUDIT_ACTION_TYPE_CHOICES = [
    ("login", "User Login"),
    ("failed_login", "Failed User Login"),
    ("delete", "Delete Object"),
    ("modify", "Modify Object"),
    ("add", "Add Object"),
    ("view", "View Object"),
    ("remote_session", "Remote Session"),
    ("execute_script", "Execute Script"),
    ("execute_command", "Execute Command"),
]

AUDIT_OBJECT_TYPE_CHOICES = [
    ("user", "User"),
    ("script", "Script"),
    ("agent", "Agent"),
    ("policy", "Policy"),
    ("winupdatepolicy", "Patch Policy"),
    ("client", "Client"),
    ("site", "Site"),
    ("check", "Check"),
    ("automatedtask", "Automated Task"),
    ("coresettings", "Core Settings")
]

# taskaction details format
# {
#   "action": "taskcreate" | "taskdelete" | "tasktoggle",
#   "value": "Enable" | "Disable" # only needed for task toggle,
#   "task_id": 1
# }

STATUS_CHOICES = [
    ("pending", "Pending"),
    ("completed", "Completed"),
]

class AuditLog(models.Model):
    username = models.CharField(max_length=100)
    agent = models.CharField(max_length=255, null=True, blank=True)
    entry_time = models.DateTimeField(auto_now_add=True)
    action = models.CharField(
        max_length=100, choices=AUDIT_ACTION_TYPE_CHOICES
    )
    object_type = models.CharField(
        max_length=100, choices=AUDIT_OBJECT_TYPE_CHOICES
    )
    before_value = models.JSONField(null=True, blank=True)
    after_value = models.JSONField(null=True, blank=True)
    message = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.username} {self.action} {self.object_type}"

    @staticmethod
    def audit_mesh_session(username, hostname):
        AuditLog.objects.create(
            username=username, 
            agent=hostname, 
            object_type="agent",
            action="remote_session", 
            message=f"{username} used Mesh Central to initiate a remote session to {hostname}.",
        )
    
    @staticmethod
    def audit_raw_command(username, hostname, cmd, shell):
        AuditLog.objects.create(
            username=username, 
            agent=hostname, 
            object_type="agent",
            action="execute_command", 
            message=f"{username} issued {shell} command on {hostname}.",
            after_value=cmd,
        )

    @staticmethod
    def audit_object_changed(username, object_type, before, after, name=""):
        AuditLog.objects.create(
            username=username,
            object_type=object_type,
            action="modify", 
            message=f"{username} modified {object_type} {name}",
            before_value=before,
            after_value=after,
        )

    @staticmethod
    def audit_object_add(username, object_type, after, name=""):
        AuditLog.objects.create(
            username=username,
            object_type=object_type,
            action="add", 
            message=f"{username} added {object_type} {name}",
            after_value=after,
        )

    @staticmethod
    def audit_object_delete(username, object_type, before, name=""):
        AuditLog.objects.create(
            username=username,
            object_type=object_type,
            action="delete", 
            message=f"{username} deleted {object_type} {name}",
            before_value=before,
        )

    @staticmethod
    def audit_script_run(username, hostname, script):
        AuditLog.objects.create(
            username=username,
            object_type="agent",
            action="execute_script", 
            message=f"{username} ran script: \"{script}\" on {hostname}",
        )

    @staticmethod
    def audit_user_failed_login(username):
        AuditLog.objects.create(
            username=username,
            object_type="user",
            action="failed_login", 
            message=f"{username} failed to login: Credentials were rejected",
        )

    @staticmethod
    def audit_user_failed_twofactor(username):
        AuditLog.objects.create(
            username=username,
            object_type="user",
            action="failed_login", 
            message=f"{username} failed to login: Two Factor token rejected",
        )

    @staticmethod
    def audit_user_login_successful(username):
        AuditLog.objects.create(
            username=username,
            object_type="user",
            action="login", 
            message=f"{username} logged in successfully",
        )

class DebugLog(models.Model):
    pass

class PendingAction(models.Model):

    agent = models.ForeignKey(
        Agent,
        related_name="pendingactions",
        on_delete=models.CASCADE,
    )
    entry_time = models.DateTimeField(auto_now_add=True)
    action_type = models.CharField(
        max_length=255, choices=ACTION_TYPE_CHOICES, null=True, blank=True
    )
    status = models.CharField(
        max_length=255,
        choices=STATUS_CHOICES,
        default="pending",
    )
    celery_id = models.CharField(null=True, blank=True, max_length=255)
    details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.agent.hostname} - {self.action_type}"

    @property
    def due(self):
        if self.action_type == "schedreboot":
            obj = dt.datetime.strptime(self.details["time"], "%Y-%m-%d %H:%M:%S")
            return dt.datetime.strftime(obj, "%B %d, %Y at %I:%M %p")

        elif self.action_type == "taskaction":
            return "Next agent check-in"

    @property
    def description(self):
        if self.action_type == "schedreboot":
            return "Device pending reboot"

        elif self.action_type == "taskaction":
            if self.details["action"] == "taskdelete":
                return "Device pending task deletion"
            elif self.details["action"] == "taskcreate":
                return "Device pending task creation"
            elif self.details["action"] == "tasktoggle":
                # value is bool
                if self.details["value"]:
                    action = "enable"
                else:
                    action = "disable"

                return f"Device pending task {action}"
