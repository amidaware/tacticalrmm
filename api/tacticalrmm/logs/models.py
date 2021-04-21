import datetime as dt
from abc import abstractmethod

from django.db import models

from tacticalrmm.middleware import get_debug_info, get_username

ACTION_TYPE_CHOICES = [
    ("schedreboot", "Scheduled Reboot"),
    ("taskaction", "Scheduled Task Action"),  # deprecated
    ("agentupdate", "Agent Update"),
    ("chocoinstall", "Chocolatey Software Install"),
]

AUDIT_ACTION_TYPE_CHOICES = [
    ("login", "User Login"),
    ("failed_login", "Failed User Login"),
    ("delete", "Delete Object"),
    ("modify", "Modify Object"),
    ("add", "Add Object"),
    ("view", "View Object"),
    ("check_run", "Check Run"),
    ("task_run", "Task Run"),
    ("agent_install", "Agent Install"),
    ("remote_session", "Remote Session"),
    ("execute_script", "Execute Script"),
    ("execute_command", "Execute Command"),
    ("bulk_action", "Bulk Action"),
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
    ("coresettings", "Core Settings"),
    ("bulk", "Bulk"),
]

STATUS_CHOICES = [
    ("pending", "Pending"),
    ("completed", "Completed"),
]


class AuditLog(models.Model):
    username = models.CharField(max_length=100)
    agent = models.CharField(max_length=255, null=True, blank=True)
    entry_time = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100, choices=AUDIT_ACTION_TYPE_CHOICES)
    object_type = models.CharField(max_length=100, choices=AUDIT_OBJECT_TYPE_CHOICES)
    before_value = models.JSONField(null=True, blank=True)
    after_value = models.JSONField(null=True, blank=True)
    message = models.CharField(max_length=255, null=True, blank=True)
    debug_info = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} {self.action} {self.object_type}"

    def save(self, *args, **kwargs):

        if not self.pk and self.message:
            # truncate message field if longer than 255 characters
            self.message = (
                (self.message[:253] + "..") if len(self.message) > 255 else self.message
            )

        return super(AuditLog, self).save(*args, **kwargs)

    @staticmethod
    def audit_mesh_session(username, hostname, debug_info={}):
        AuditLog.objects.create(
            username=username,
            agent=hostname,
            object_type="agent",
            action="remote_session",
            message=f"{username} used Mesh Central to initiate a remote session to {hostname}.",
            debug_info=debug_info,
        )

    @staticmethod
    def audit_raw_command(username, hostname, cmd, shell, debug_info={}):
        AuditLog.objects.create(
            username=username,
            agent=hostname,
            object_type="agent",
            action="execute_command",
            message=f"{username} issued {shell} command on {hostname}.",
            after_value=cmd,
            debug_info=debug_info,
        )

    @staticmethod
    def audit_object_changed(
        username, object_type, before, after, name="", debug_info={}
    ):
        AuditLog.objects.create(
            username=username,
            object_type=object_type,
            action="modify",
            message=f"{username} modified {object_type} {name}",
            before_value=before,
            after_value=after,
            debug_info=debug_info,
        )

    @staticmethod
    def audit_object_add(username, object_type, after, name="", debug_info={}):
        AuditLog.objects.create(
            username=username,
            object_type=object_type,
            action="add",
            message=f"{username} added {object_type} {name}",
            after_value=after,
            debug_info=debug_info,
        )

    @staticmethod
    def audit_object_delete(username, object_type, before, name="", debug_info={}):
        AuditLog.objects.create(
            username=username,
            object_type=object_type,
            action="delete",
            message=f"{username} deleted {object_type} {name}",
            before_value=before,
            debug_info=debug_info,
        )

    @staticmethod
    def audit_script_run(username, hostname, script, debug_info={}):
        AuditLog.objects.create(
            agent=hostname,
            username=username,
            object_type="agent",
            action="execute_script",
            message=f'{username} ran script: "{script}" on {hostname}',
            debug_info=debug_info,
        )

    @staticmethod
    def audit_user_failed_login(username, debug_info={}):
        AuditLog.objects.create(
            username=username,
            object_type="user",
            action="failed_login",
            message=f"{username} failed to login: Credentials were rejected",
            debug_info=debug_info,
        )

    @staticmethod
    def audit_user_failed_twofactor(username, debug_info={}):
        AuditLog.objects.create(
            username=username,
            object_type="user",
            action="failed_login",
            message=f"{username} failed to login: Two Factor token rejected",
            debug_info=debug_info,
        )

    @staticmethod
    def audit_user_login_successful(username, debug_info={}):
        AuditLog.objects.create(
            username=username,
            object_type="user",
            action="login",
            message=f"{username} logged in successfully",
            debug_info=debug_info,
        )

    @staticmethod
    def audit_bulk_action(username, action, affected, debug_info={}):
        from agents.models import Agent
        from clients.models import Client, Site
        from scripts.models import Script

        target = ""
        agents = None

        if affected["target"] == "all":
            target = "on all agents"
        elif affected["target"] == "client":
            client = Client.objects.get(pk=affected["client"])
            target = f"on all agents within client: {client.name}"
        elif affected["target"] == "site":
            site = Site.objects.get(pk=affected["site"])
            target = f"on all agents within site: {site.client.name}\\{site.name}"
        elif affected["target"] == "agents":
            agents = Agent.objects.filter(pk__in=affected["agentPKs"]).values_list(
                "hostname", flat=True
            )
            target = "on multiple agents"

        if action == "script":
            script = Script.objects.get(pk=affected["scriptPK"])
            action = f"script: {script.name}"

        if agents:
            affected["agent_hostnames"] = list(agents)

        AuditLog.objects.create(
            username=username,
            object_type="bulk",
            action="bulk_action",
            message=f"{username} executed bulk {action} {target}",
            debug_info=debug_info,
            after_value=affected,
        )


class DebugLog(models.Model):
    pass


class PendingAction(models.Model):

    agent = models.ForeignKey(
        "agents.Agent",
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
        elif self.action_type == "agentupdate":
            return "Next update cycle"
        elif self.action_type == "chocoinstall":
            return "ASAP"

    @property
    def description(self):
        if self.action_type == "schedreboot":
            return "Device pending reboot"

        elif self.action_type == "agentupdate":
            return f"Agent update to {self.details['version']}"

        elif self.action_type == "chocoinstall":
            return f"{self.details['name']} software install"


class BaseAuditModel(models.Model):
    # abstract base class for auditing models
    class Meta:
        abstract = True

    # create audit fields
    created_by = models.CharField(max_length=100, null=True, blank=True)
    created_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_by = models.CharField(max_length=100, null=True, blank=True)
    modified_time = models.DateTimeField(auto_now=True, null=True, blank=True)

    @abstractmethod
    def serialize():
        pass

    def save(self, *args, **kwargs):
        if get_username():

            before_value = {}
            object_class = type(self)
            object_name = object_class.__name__.lower()
            username = get_username()

            # populate created_by and modified_by fields on instance
            if not getattr(self, "created_by", None):
                self.created_by = username
            if hasattr(self, "modified_by"):
                self.modified_by = username

            # capture object properties before edit
            if self.pk:
                before_value = object_class.objects.get(pk=self.id)

            # dont create entry for agent add since that is done in view
            if not self.pk:
                AuditLog.audit_object_add(
                    username,
                    object_name,
                    object_class.serialize(self),
                    self.__str__(),
                    debug_info=get_debug_info(),
                )
            else:
                AuditLog.audit_object_changed(
                    username,
                    object_class.__name__.lower(),
                    object_class.serialize(before_value),
                    object_class.serialize(self),
                    self.__str__(),
                    debug_info=get_debug_info(),
                )

        return super(BaseAuditModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):

        if get_username():

            object_class = type(self)
            AuditLog.audit_object_delete(
                get_username(),
                object_class.__name__.lower(),
                object_class.serialize(self),
                self.__str__(),
                debug_info=get_debug_info(),
            )

        return super(BaseAuditModel, self).delete(*args, **kwargs)
