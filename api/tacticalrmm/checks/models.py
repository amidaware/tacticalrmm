import string
import os
import json

from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.validators import MinValueValidator, MaxValueValidator

CHECK_TYPE_CHOICES = [
    ("diskspace", "Disk Space Check"),
    ("ping", "Ping Check"),
    ("cpuload", "CPU Load Check"),
    ("memory", "Memory Check"),
    ("winsvc", "Win Service Check"),
    ("script", "Script Check"),
    ("eventlog", "Event Log Check"),
]

CHECK_STATUS_CHOICES = [
    ("passing", "Passing"),
    ("failing", "Failing"),
    ("pending", "Pending"),
]

EVT_LOG_NAME_CHOICES = [
    ("Application", "Application"),
    ("System", "System"),
    ("Security", "Security"),
]

EVT_LOG_TYPE_CHOICES = [
    ("INFO", "Information"),
    ("WARNING", "Warning"),
    ("ERROR", "Error"),
    ("AUDIT_SUCCESS", "Success Audit"),
    ("AUDIT_FAILURE", "Failure Audit"),
]

EVT_LOG_FAIL_WHEN_CHOICES = [
    ("contains", "Log contains"),
    ("not_contains", "Log does not contain"),
]


class Check(models.Model):

    # common fields

    agent = models.ForeignKey(
        "agents.Agent",
        related_name="agentchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    policy = models.ForeignKey(
        "automation.Policy",
        related_name="policychecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    check_type = models.CharField(
        max_length=50, choices=CHECK_TYPE_CHOICES, default="diskspace"
    )
    status = models.CharField(
        max_length=100, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    more_info = models.TextField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    fails_b4_alert = models.PositiveIntegerField(default=1)
    fail_count = models.PositiveIntegerField(default=0)
    email_sent = models.DateTimeField(null=True, blank=True)
    text_sent = models.DateTimeField(null=True, blank=True)
    outage_history = JSONField(null=True, blank=True)  # store
    extra_details = JSONField(null=True, blank=True)

    # check specific fields

    # threshold percent for diskspace, cpuload or memory check
    threshold = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    # diskcheck i.e C:, D: etc
    disk = models.CharField(max_length=2, null=True, blank=True)
    # ping checks
    ip = models.CharField(max_length=255, null=True, blank=True)
    # script checks
    script = models.ForeignKey(
        "scripts.Script",
        related_name="script",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    timeout = models.PositiveIntegerField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    retcode = models.IntegerField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, null=True, blank=True)
    # cpu and mem check history
    history = ArrayField(
        models.IntegerField(blank=True), null=True, blank=True, default=list
    )
    # win service checks
    svc_name = models.CharField(max_length=255, null=True, blank=True)
    svc_display_name = models.CharField(max_length=255, null=True, blank=True)
    pass_if_start_pending = models.BooleanField(null=True, blank=True)
    restart_if_stopped = models.BooleanField(null=True, blank=True)
    # event log checks
    log_name = models.CharField(
        max_length=255, choices=EVT_LOG_NAME_CHOICES, null=True, blank=True
    )
    event_id = models.IntegerField(null=True, blank=True)
    event_type = models.CharField(
        max_length=255, choices=EVT_LOG_TYPE_CHOICES, null=True, blank=True
    )
    fail_when = models.CharField(
        max_length=255, choices=EVT_LOG_FAIL_WHEN_CHOICES, null=True, blank=True
    )
    search_last_days = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        if self.agent:
            return f"{self.agent.hostname} - {self.check_type}"
        else:
            return f"{self.policy.name} - {self.check_type}"

    @property
    def readable_desc(self):
        if self.check_type == "diskspace":
            return f"{self.get_check_type_display()}: Drive {self.disk} < {self.threshold}%"
        elif self.check_type == "ping":
            return f"{self.get_check_type_display()}: {self.ip}"
        elif self.check_type == "cpuload" or self.check_type == "memory":
            return f"{self.get_check_type_display()} > {self.threshold}%"
        elif self.check_type == "winsvc":
            return f"{self.get_check_type_display()}: {self.svc_display_name}"
        elif self.check_type == "script" or self.check_type == "eventlog":
            return f"{self.get_check_type_display()}: {self.name}"
        else:
            return "n/a"

    # for policy diskchecks
    @staticmethod
    def all_disks():
        return [f"{i}:" for i in string.ascii_uppercase]

    # for policy service checks
    @staticmethod
    def load_default_services():
        with open(
            os.path.join(settings.BASE_DIR, "services/default_services.json")
        ) as f:
            default_services = json.load(f)

        return default_services
