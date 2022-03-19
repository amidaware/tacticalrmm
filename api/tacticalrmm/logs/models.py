import datetime as dt
from abc import abstractmethod

from django.db import models

from tacticalrmm.middleware import get_debug_info, get_username
from tacticalrmm.models import PermissionQuerySet


def get_debug_level():
    from core.models import CoreSettings

    return CoreSettings.objects.first().agent_debug_level  # type: ignore


ACTION_TYPE_CHOICES = [
    ("schedreboot", "Scheduled Reboot"),
    ("agentupdate", "Agent Update"),
    ("chocoinstall", "Chocolatey Software Install"),
    ("runcmd", "Run Command"),
    ("runscript", "Run Script"),
    ("runpatchscan", "Run Patch Scan"),
    ("runpatchinstall", "Run Patch Install"),
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
    ("url_action", "URL Action"),
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
    ("alerttemplate", "Alert Template"),
    ("role", "Role"),
    ("urlaction", "URL Action"),
    ("keystore", "Global Key Store"),
    ("customfield", "Custom Field"),
]

STATUS_CHOICES = [
    ("pending", "Pending"),
    ("completed", "Completed"),
]


class AuditLog(models.Model):
    username = models.CharField(max_length=255)
    agent = models.CharField(max_length=255, null=True, blank=True)
    agent_id = models.CharField(max_length=255, blank=True, null=True)
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
    def audit_mesh_session(username, agent, debug_info={}):
        AuditLog.objects.create(
            username=username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type="agent",
            action="remote_session",
            message=f"{username} used Mesh Central to initiate a remote session to {agent.hostname}.",
            debug_info=debug_info,
        )

    @staticmethod
    def audit_raw_command(username, agent, cmd, shell, debug_info={}):
        AuditLog.objects.create(
            username=username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type="agent",
            action="execute_command",
            message=f"{username} issued {shell} command on {agent.hostname}.",
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
            agent=before["hostname"] if object_type == "agent" else None,
            agent_id=before["agent_id"] if object_type == "agent" else None,
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
            agent=after["hostname"] if object_type == "agent" else None,
            agent_id=after["agent_id"] if object_type == "agent" else None,
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
            agent=before["hostname"] if object_type == "agent" else None,
            agent_id=before["agent_id"] if object_type == "agent" else None,
            action="delete",
            message=f"{username} deleted {object_type} {name}",
            before_value=before,
            debug_info=debug_info,
        )

    @staticmethod
    def audit_script_run(username, agent, script, debug_info={}):
        AuditLog.objects.create(
            agent=agent.hostname,
            agent_id=agent.agent_id,
            username=username,
            object_type="agent",
            action="execute_script",
            message=f'{username} ran script: "{script}" on {agent.hostname}',
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
    def audit_url_action(username, urlaction, instance, debug_info={}):

        name = instance.hostname if hasattr(instance, "hostname") else instance.name
        classname = type(instance).__name__
        AuditLog.objects.create(
            username=username,
            agent=instance.hostname if classname == "Agent" else None,
            agent_id=instance.agent_id if classname == "Agent" else None,
            object_type=classname.lower(),
            action="url_action",
            message=f"{username} ran url action: {urlaction.pattern} on {classname}: {name}",
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
            agents = Agent.objects.filter(agent_id__in=affected["agents"]).values_list(
                "hostname", flat=True
            )
            target = "on multiple agents"

        if action == "script":
            script = Script.objects.get(pk=affected["script"])
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


LOG_LEVEL_CHOICES = [
    ("info", "Info"),
    ("warning", "Warning"),
    ("error", "Error"),
    ("critical", "Critical"),
]

LOG_TYPE_CHOICES = [
    ("agent_update", "Agent Update"),
    ("agent_issues", "Agent Issues"),
    ("win_updates", "Windows Updates"),
    ("system_issues", "System Issues"),
    ("scripting", "Scripting"),
]


class DebugLog(models.Model):
    objects = PermissionQuerySet.as_manager()

    entry_time = models.DateTimeField(auto_now_add=True)
    agent = models.ForeignKey(
        "agents.Agent",
        related_name="debuglogs",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    log_level = models.CharField(
        max_length=50, choices=LOG_LEVEL_CHOICES, default="info"
    )
    log_type = models.CharField(
        max_length=50, choices=LOG_TYPE_CHOICES, default="system_issues"
    )
    message = models.TextField(null=True, blank=True)

    @classmethod
    def info(
        cls,
        message,
        agent=None,
        log_type="system_issues",
    ):
        if get_debug_level() in ["info"]:
            cls.objects.create(
                log_level="info", agent=agent, log_type=log_type, message=message
            )

    @classmethod
    def warning(cls, message, agent=None, log_type="system_issues"):
        if get_debug_level() in ["info", "warning"]:
            cls.objects.create(
                log_level="warning", agent=agent, log_type=log_type, message=message
            )

    @classmethod
    def error(cls, message, agent=None, log_type="system_issues"):
        if get_debug_level() in ["info", "warning", "error"]:
            cls.objects.create(
                log_level="error", agent=agent, log_type=log_type, message=message
            )

    @classmethod
    def critical(cls, message, agent=None, log_type="system_issues"):
        if get_debug_level() in ["info", "warning", "error", "critical"]:
            cls.objects.create(
                log_level="critical", agent=agent, log_type=log_type, message=message
            )


class PendingAction(models.Model):
    objects = PermissionQuerySet.as_manager()

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
    cancelable = models.BooleanField(blank=True, default=False)
    celery_id = models.CharField(null=True, blank=True, max_length=255)
    details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.agent.hostname} - {self.action_type}"

    @property
    def due(self):
        if self.action_type == "schedreboot":
            return self.details["time"]
        elif self.action_type == "agentupdate":
            return "Next update cycle"
        elif self.action_type == "chocoinstall":
            return "ASAP"
        else:
            return "On next checkin"

    @property
    def description(self):
        if self.action_type == "schedreboot":
            return "Device pending reboot"

        elif self.action_type == "agentupdate":
            return f"Agent update to {self.details['version']}"

        elif self.action_type == "chocoinstall":
            return f"{self.details['name']} software install"

        elif self.action_type in [
            "runcmd",
            "runscript",
            "runpatchscan",
            "runpatchinstall",
        ]:
            return f"{self.action_type}"


class BaseAuditModel(models.Model):
    # abstract base class for auditing models
    class Meta:
        abstract = True

    # create audit fields
    created_by = models.CharField(max_length=255, null=True, blank=True)
    created_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_by = models.CharField(max_length=255, null=True, blank=True)
    modified_time = models.DateTimeField(auto_now=True, null=True, blank=True)

    @abstractmethod
    def serialize():
        pass

    def save(self, old_model=None, *args, **kwargs):

        if get_username():

            object_class = type(self)
            object_name = object_class.__name__.lower()
            username = get_username()
            after_value = object_class.serialize(self)  # type: ignore

            # populate created_by and modified_by fields on instance
            if not getattr(self, "created_by", None):
                self.created_by = username
            if hasattr(self, "modified_by"):
                self.modified_by = username

            # dont create entry for agent add since that is done in view
            if not self.pk:
                AuditLog.audit_object_add(
                    username,
                    object_name,
                    after_value,  # type: ignore
                    self.__str__(),
                    debug_info=get_debug_info(),
                )
            else:

                if old_model:
                    before_value = object_class.serialize(old_model)  # type: ignore
                else:
                    before_value = object_class.serialize(object_class.objects.get(pk=self.pk))  # type: ignore
                # only create an audit entry if the values have changed
                if before_value != after_value:  # type: ignore

                    AuditLog.audit_object_changed(
                        username,
                        object_class.__name__.lower(),
                        before_value,
                        after_value,  # type: ignore
                        self.__str__(),
                        debug_info=get_debug_info(),
                    )

        super(BaseAuditModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super(BaseAuditModel, self).delete(*args, **kwargs)

        if get_username():

            object_class = type(self)
            AuditLog.audit_object_delete(
                get_username(),
                object_class.__name__.lower(),
                object_class.serialize(self),  # type: ignore
                self.__str__(),
                debug_info=get_debug_info(),
            )
