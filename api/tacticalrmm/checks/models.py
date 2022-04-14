from statistics import mean
from typing import TYPE_CHECKING, Any, Union, Dict, Optional

from django.core.cache import cache
from alerts.models import SEVERITY_CHOICES
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from logs.models import BaseAuditModel

from tacticalrmm.models import PermissionQuerySet
from core.utils import get_core_settings

if TYPE_CHECKING:
    from alerts.models import Alert, AlertTemplate  # pragma: no cover
    from automation.models import Policy  # pragma: no cover

CHECK_TYPE_CHOICES = [
    ("diskspace", "Disk Space Check"),
    ("ping", "Ping Check"),
    ("cpuload", "CPU Load Check"),
    ("memory", "Memory Check"),
    ("winsvc", "Service Check"),
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


class Check(BaseAuditModel):
    objects = PermissionQuerySet.as_manager()

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
    overridden_by_policy = models.BooleanField(default=False)
    name = models.CharField(max_length=255, null=True, blank=True)
    check_type = models.CharField(
        max_length=50, choices=CHECK_TYPE_CHOICES, default="diskspace"
    )
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    dashboard_alert = models.BooleanField(default=False)
    fails_b4_alert = models.PositiveIntegerField(default=1)
    run_interval = models.PositiveIntegerField(blank=True, default=0)
    # check specific fields

    # for eventlog, script, ip, and service alert severity
    alert_severity = models.CharField(
        max_length=15,
        choices=SEVERITY_CHOICES,
        default="warning",
        null=True,
        blank=True,
    )

    # threshold percent for diskspace, cpuload or memory check
    error_threshold = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(99)],
        null=True,
        blank=True,
        default=0,
    )
    warning_threshold = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(99)],
        default=0,
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
    script_args = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    info_return_codes = ArrayField(
        models.PositiveIntegerField(),
        null=True,
        blank=True,
        default=list,
    )
    warning_return_codes = ArrayField(
        models.PositiveIntegerField(),
        null=True,
        blank=True,
        default=list,
    )
    timeout = models.PositiveIntegerField(null=True, blank=True)
    # win service checks
    svc_name = models.CharField(max_length=255, null=True, blank=True)
    svc_display_name = models.CharField(max_length=255, null=True, blank=True)
    pass_if_start_pending = models.BooleanField(null=True, blank=True)
    pass_if_svc_not_exist = models.BooleanField(default=False)
    restart_if_stopped = models.BooleanField(null=True, blank=True)
    svc_policy_mode = models.CharField(
        max_length=20, null=True, blank=True
    )  # 'default' or 'manual', for editing policy check

    # event log checks
    log_name = models.CharField(
        max_length=255, choices=EVT_LOG_NAME_CHOICES, null=True, blank=True
    )
    event_id = models.IntegerField(null=True, blank=True)
    event_id_is_wildcard = models.BooleanField(default=False)
    event_type = models.CharField(
        max_length=255, choices=EVT_LOG_TYPE_CHOICES, null=True, blank=True
    )
    event_source = models.CharField(max_length=255, null=True, blank=True)
    event_message = models.TextField(null=True, blank=True)
    fail_when = models.CharField(
        max_length=255, choices=EVT_LOG_FAIL_WHEN_CHOICES, null=True, blank=True
    )
    search_last_days = models.PositiveIntegerField(null=True, blank=True)
    number_of_events_b4_alert = models.PositiveIntegerField(
        null=True, blank=True, default=1
    )

    # deprecated
    managed_by_policy = models.BooleanField(default=False)

    # non-database property
    check_result: "Union[CheckResult, Dict[None, None]]" = {}

    def __str__(self):
        if self.agent:
            return f"{self.agent.hostname} - {self.readable_desc}"
        else:
            return f"{self.policy.name} - {self.readable_desc}"

    def save(self, *args, **kwargs):

        # if check is a policy check clear cache on everything
        if self.policy:
            cache.delete_many_pattern("site_*_checks")
            cache.delete_many_pattern("agent_*_checks")

        # if check is an agent check
        elif self.agent:
            cache.delete(f"agent_{self.agent.agent_id}_checks")

        super(Check, self).save(
            *args,
            **kwargs,
        )

    def delete(self, *args, **kwargs):

        # if check is a policy check clear cache on everything
        if self.policy:
            cache.delete_many_pattern("site_*_checks")
            cache.delete_many_pattern("agent_*_checks")

        # if check is an agent check
        elif self.agent:
            cache.delete(f"agent_{self.agent.agent_id}_checks")

        super(Check, self).delete(
            *args,
            **kwargs,
        )

    @property
    def readable_desc(self):
        display = self.get_check_type_display()  # type: ignore
        if self.check_type == "diskspace":

            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            return f"{display}: Drive {self.disk} - {text}"
        elif self.check_type == "ping":
            return f"{display}: {self.name}"
        elif self.check_type == "cpuload" or self.check_type == "memory":

            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            return f"{display} - {text}"
        elif self.check_type == "winsvc":
            return f"{display}: {self.svc_display_name}"
        elif self.check_type == "eventlog":
            return f"{display}: {self.name}"
        elif self.check_type == "script":
            return f"{display}: {self.script.name}"
        else:
            return "n/a"

    @staticmethod
    def non_editable_fields() -> list[str]:
        return [
            "check_type",
            "readable_desc",
            "overridden_by_policy",
            "created_by",
            "created_time",
            "modified_by",
            "modified_time",
        ]

    def create_policy_check(self, policy: "Policy") -> None:

        fields_to_copy = [
            "warning_threshold",
            "error_threshold",
            "alert_severity",
            "name",
            "run_interval",
            "disk",
            "fails_b4_alert",
            "ip",
            "script",
            "script_args",
            "info_return_codes",
            "warning_return_codes",
            "timeout",
            "svc_name",
            "svc_display_name",
            "svc_policy_mode",
            "pass_if_start_pending",
            "pass_if_svc_not_exist",
            "restart_if_stopped",
            "log_name",
            "event_id",
            "event_id_is_wildcard",
            "event_type",
            "event_source",
            "event_message",
            "fail_when",
            "search_last_days",
            "number_of_events_b4_alert",
            "email_alert",
            "text_alert",
            "dashboard_alert",
        ]

        check = Check.objects.create(
            policy=policy,
        )

        for task in self.assignedtasks.all():  # type: ignore
            task.create_policy_task(policy=policy, assigned_check=check)

        for field in fields_to_copy:
            setattr(check, field, getattr(self, field))

        check.save()

    def should_create_alert(self, alert_template=None):

        return (
            self.dashboard_alert
            or self.email_alert
            or self.text_alert
            or (
                alert_template
                and (
                    alert_template.check_always_alert
                    or alert_template.check_always_email
                    or alert_template.check_always_text
                )
            )
        )

    def add_check_history(
        self, value: int, agent_id: str, more_info: Any = None
    ) -> None:
        CheckHistory.objects.create(
            check_id=self.pk, y=value, results=more_info, agent_id=agent_id
        )

    def handle_assigned_task(self) -> None:
        for task in self.assignedtasks.all():  # type: ignore
            if task.enabled:
                task.run_win_task()

    @staticmethod
    def serialize(check):
        # serializes the check and returns json
        from .serializers import CheckAuditSerializer

        return CheckAuditSerializer(check).data

    def is_duplicate(self, check):
        if self.check_type == "diskspace":
            return self.disk == check.disk

        elif self.check_type == "script":
            return self.script == check.script

        elif self.check_type == "ping":
            return self.ip == check.ip

        elif self.check_type == "cpuload":
            return True

        elif self.check_type == "memory":
            return True

        elif self.check_type == "winsvc":
            return self.svc_name == check.svc_name

        elif self.check_type == "eventlog":
            return [self.log_name, self.event_id] == [check.log_name, check.event_id]


class CheckResult(models.Model):
    objects = PermissionQuerySet.as_manager()

    class Meta:
        unique_together = (("agent", "assigned_check"),)

    agent = models.ForeignKey(
        "agents.Agent",
        related_name="checkresults",
        on_delete=models.CASCADE,
    )

    assigned_check = models.ForeignKey(
        "checks.Check",
        related_name="checkresults",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=100, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    # for memory, diskspace, script, and cpu checks where severity changes
    alert_severity = models.CharField(
        max_length=15,
        choices=SEVERITY_CHOICES,
        default="warning",
        null=True,
        blank=True,
    )
    more_info = models.TextField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    fail_count = models.PositiveIntegerField(default=0)
    outage_history = models.JSONField(null=True, blank=True)  # store
    extra_details = models.JSONField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    retcode = models.IntegerField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, null=True, blank=True)
    # cpu and mem check history
    history = ArrayField(
        models.IntegerField(blank=True), null=True, blank=True, default=list
    )

    def __str__(self):
        return f"{self.agent.hostname} - {self.assigned_check}"

    @property
    def history_info(self):
        if (
            self.assigned_check.check_type == "cpuload"
            or self.assigned_check.check_type == "memory"
        ):
            return ", ".join(str(f"{x}%") for x in self.history[-6:])

    def get_or_create_alert_if_needed(
        self, alert_template: "Optional[AlertTemplate]"
    ) -> "Optional[Alert]":
        from alerts.models import Alert

        return Alert.create_or_return_check_alert(
            self.assigned_check,
            agent=self.agent,
            alert_severity=self.alert_severity,
            skip_create=not self.assigned_check.should_create_alert(alert_template),
        )

    def handle_check(self, data):
        from alerts.models import Alert

        check = self.assigned_check

        # cpuload or mem checks
        if check.check_type == "cpuload" or check.check_type == "memory":

            self.history.append(data["percent"])

            if len(self.history) > 15:
                self.history = self.history[-15:]

            self.save(update_fields=["history"])

            avg = int(mean(self.history))

            if check.error_threshold and avg > check.error_threshold:
                self.status = "failing"
                self.alert_severity = "error"
            elif check.warning_threshold and avg > check.warning_threshold:
                self.status = "failing"
                self.alert_severity = "warning"
            else:
                self.status = "passing"

            # add check history
            check.add_check_history(data["percent"], self.agent.agent_id)

        # diskspace checks
        elif check.check_type == "diskspace":
            if data["exists"]:
                percent_used = round(data["percent_used"])
                if (
                    check.error_threshold
                    and (100 - percent_used) < check.error_threshold
                ):
                    self.status = "failing"
                    self.alert_severity = "error"
                elif (
                    check.warning_threshold
                    and (100 - percent_used) < check.warning_threshold
                ):
                    self.status = "failing"
                    self.alert_severity = "warning"

                else:
                    self.status = "passing"

                self.more_info = data["more_info"]

                # add check history
                check.add_check_history(100 - percent_used, self.agent.agent_id)
            else:
                self.status = "failing"
                self.alert_severity = "error"
                self.more_info = f"Disk {check.disk} does not exist"

            self.save(update_fields=["more_info"])

        # script checks
        elif check.check_type == "script":
            self.stdout = data["stdout"]
            self.stderr = data["stderr"]
            self.retcode = data["retcode"]
            self.execution_time = "{:.4f}".format(data["runtime"])

            if data["retcode"] in check.info_return_codes:
                self.alert_severity = "info"
                self.status = "failing"
            elif data["retcode"] in check.warning_return_codes:
                self.alert_severity = "warning"
                self.status = "failing"
            elif data["retcode"] != 0:
                self.status = "failing"
                self.alert_severity = "error"
            else:
                self.status = "passing"

            self.save(
                update_fields=[
                    "stdout",
                    "stderr",
                    "retcode",
                    "execution_time",
                ]
            )

            # add check history
            check.add_check_history(
                1 if self.status == "failing" else 0,
                self.agent.agent_id,
                {
                    "retcode": data["retcode"],
                    "stdout": data["stdout"][:60],
                    "stderr": data["stderr"][:60],
                    "execution_time": self.execution_time,
                },
            )

        # ping checks
        elif check.check_type == "ping":
            self.status = data["status"]
            self.more_info = data["output"]
            self.save(update_fields=["more_info"])

            check.add_check_history(
                1 if self.status == "failing" else 0,
                self.agent.agent_id,
                self.more_info[:60],
            )

        # windows service checks
        elif check.check_type == "winsvc":
            self.status = data["status"]
            self.more_info = data["more_info"]
            self.save(update_fields=["more_info"])

            check.add_check_history(
                1 if self.status == "failing" else 0,
                self.agent.agent_id,
                self.more_info[:60],
            )

        elif check.check_type == "eventlog":
            log = data["log"]
            if check.fail_when == "contains":
                if log and len(log) >= check.number_of_events_b4_alert:
                    self.status = "failing"
                else:
                    self.status = "passing"

            elif check.fail_when == "not_contains":
                if log and len(log) >= check.number_of_events_b4_alert:
                    self.status = "passing"
                else:
                    self.status = "failing"

            self.extra_details = {"log": log}
            self.save(update_fields=["extra_details"])

            check.add_check_history(
                1 if self.status == "failing" else 0,
                self.agent.agent_id,
                "Events Found:" + str(len(self.extra_details["log"])),
            )

        # handle status
        if self.status == "failing":
            self.fail_count += 1
            self.save(update_fields=["status", "fail_count", "alert_severity"])

            if self.fail_count >= check.fails_b4_alert:
                Alert.handle_alert_failure(self)

        elif self.status == "passing":
            self.fail_count = 0
            self.save(update_fields=["status", "fail_count", "alert_severity"])
            if Alert.objects.filter(
                assigned_check=check, agent=self.agent, resolved=False
            ).exists():
                Alert.handle_alert_resolve(self)

        return self.status

    def send_email(self):

        CORE = get_core_settings()

        body: str = ""
        if self.agent:
            subject = f"{self.agent.client.name}, {self.agent.site.name}, {self.agent.hostname} - {self} Failed"
        else:
            subject = f"{self} Failed"

        if self.assigned_check.check_type == "diskspace":
            text = ""
            if self.assigned_check.warning_threshold:
                text += f" Warning Threshold: {self.assigned_check.warning_threshold}%"
            if self.assigned_check.error_threshold:
                text += f" Error Threshold: {self.assigned_check.error_threshold}%"

            try:
                percent_used = [
                    d["percent"]
                    for d in self.agent.disks
                    if d["device"] == self.assigned_check.disk
                ][0]
                percent_free = 100 - percent_used

                body = subject + f" - Free: {percent_free}%, {text}"
            except:
                body = subject + f" - Disk {self.assigned_check.disk} does not exist"

        elif self.assigned_check.check_type == "script":

            body = (
                subject
                + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
            )

        elif self.assigned_check.check_type == "ping":

            body = self.more_info

        elif (
            self.assigned_check.check_type == "cpuload"
            or self.assigned_check.check_type == "memory"
        ):
            text = ""
            if self.assigned_check.warning_threshold:
                text += f" Warning Threshold: {self.assigned_check.warning_threshold}%"
            if self.assigned_check.error_threshold:
                text += f" Error Threshold: {self.assigned_check.error_threshold}%"

            avg = int(mean(self.history))

            if self.assigned_check.check_type == "cpuload":
                body = subject + f" - Average CPU utilization: {avg}%, {text}"

            elif self.assigned_check.check_type == "memory":
                body = subject + f" - Average memory usage: {avg}%, {text}"

        elif self.assigned_check.check_type == "winsvc":
            body = subject + f" - Status: {self.more_info}"

        elif self.assigned_check.check_type == "eventlog":

            if self.assigned_check.event_source and self.assigned_check.event_message:
                start = f"Event ID {self.assigned_check.event_id}, source {self.assigned_check.event_source}, containing string {self.assigned_check.event_message} "
            elif self.assigned_check.event_source:
                start = f"Event ID {self.assigned_check.event_id}, source {self.assigned_check.event_source} "
            elif self.assigned_check.event_message:
                start = f"Event ID {self.assigned_check.event_id}, containing string {self.assigned_check.event_message} "
            else:
                start = f"Event ID {self.assigned_check.event_id} "

            body = start + f"was found in the {self.assigned_check.log_name} log\n\n"

            for i in self.extra_details["log"]:
                try:
                    if i["message"]:
                        body += f"{i['message']}\n"
                except:
                    continue

        CORE.send_mail(subject, body, alert_template=self.agent.alert_template)

    def send_sms(self):

        CORE = get_core_settings()
        body: str = ""

        if self.agent:
            subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Failed"
        else:
            subject = f"{self} Failed"

        if self.assigned_check.check_type == "diskspace":
            text = ""
            if self.assigned_check.warning_threshold:
                text += f" Warning Threshold: {self.assigned_check.warning_threshold}%"
            if self.assigned_check.error_threshold:
                text += f" Error Threshold: {self.assigned_check.error_threshold}%"

            try:
                percent_used = [
                    d["percent"]
                    for d in self.agent.disks
                    if d["device"] == self.assigned_check.disk
                ][0]
                percent_free = 100 - percent_used
                body = subject + f" - Free: {percent_free}%, {text}"
            except:
                body = subject + f" - Disk {self.assigned_check.disk} does not exist"

        elif self.assigned_check.check_type == "script":
            body = subject + f" - Return code: {self.retcode}"
        elif self.assigned_check.check_type == "ping":
            body = subject
        elif (
            self.assigned_check.check_type == "cpuload"
            or self.assigned_check.check_type == "memory"
        ):
            text = ""
            if self.assigned_check.warning_threshold:
                text += f" Warning Threshold: {self.assigned_check.warning_threshold}%"
            if self.assigned_check.error_threshold:
                text += f" Error Threshold: {self.assigned_check.error_threshold}%"

            avg = int(mean(self.history))
            if self.assigned_check.check_type == "cpuload":
                body = subject + f" - Average CPU utilization: {avg}%, {text}"
            elif self.assigned_check.check_type == "memory":
                body = subject + f" - Average memory usage: {avg}%, {text}"
        elif self.assigned_check.check_type == "winsvc":
            body = subject + f" - Status: {self.more_info}"
        elif self.assigned_check.check_type == "eventlog":
            body = subject

        CORE.send_sms(body, alert_template=self.agent.alert_template)

    def send_resolved_email(self):
        CORE = get_core_settings()

        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        body = f"{self} is now back to normal"

        CORE.send_mail(subject, body, alert_template=self.agent.alert_template)

    def send_resolved_sms(self):
        CORE = get_core_settings()

        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        CORE.send_sms(subject, alert_template=self.agent.alert_template)


class CheckHistory(models.Model):
    objects = PermissionQuerySet.as_manager()

    check_id = models.PositiveIntegerField(default=0)
    agent_id = models.CharField(max_length=200, null=True, blank=True)
    x = models.DateTimeField(auto_now_add=True)
    y = models.PositiveIntegerField(null=True, blank=True, default=None)
    results = models.JSONField(null=True, blank=True)

    def __str__(self):
        return str(self.x)
