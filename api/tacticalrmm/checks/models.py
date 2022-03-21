from statistics import mean
from typing import Any

from alerts.models import SEVERITY_CHOICES
from core.models import CoreSettings
from django.utils import timezone as djangotime
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from logs.models import BaseAuditModel

from tacticalrmm.models import PermissionQuerySet

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
    overriden_by_policy = models.BooleanField(default=False)
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
    dashboard_alert = models.BooleanField(default=False)
    fails_b4_alert = models.PositiveIntegerField(default=1)
    fail_count = models.PositiveIntegerField(default=0)
    outage_history = models.JSONField(null=True, blank=True)  # store
    extra_details = models.JSONField(null=True, blank=True)
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

    def __str__(self):
        if self.agent:
            return f"{self.agent.hostname} - {self.readable_desc}"
        else:
            return f"{self.policy.name} - {self.readable_desc}"

    @property
    def readable_desc(self):
        if self.check_type == "diskspace":

            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            return f"{self.get_check_type_display()}: Drive {self.disk} - {text}"  # type: ignore
        elif self.check_type == "ping":
            return f"{self.get_check_type_display()}: {self.name}"  # type: ignore
        elif self.check_type == "cpuload" or self.check_type == "memory":

            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            return f"{self.get_check_type_display()} - {text}"  # type: ignore
        elif self.check_type == "winsvc":
            return f"{self.get_check_type_display()}: {self.svc_display_name}"  # type: ignore
        elif self.check_type == "eventlog":
            return f"{self.get_check_type_display()}: {self.name}"  # type: ignore
        elif self.check_type == "script":
            return f"{self.get_check_type_display()}: {self.script.name}"  # type: ignore
        else:
            return "n/a"

    @property
    def history_info(self):
        if self.check_type == "cpuload" or self.check_type == "memory":
            return ", ".join(str(f"{x}%") for x in self.history[-6:])

    @staticmethod
    def non_editable_fields() -> list[str]:
        return [
            "check_type",
            "more_info",
            "last_run",
            "fail_count",
            "outage_history",
            "extra_details",
            "status",
            "stdout",
            "stderr",
            "retcode",
            "execution_time",
            "history",
            "readable_desc",
            "history_info",
            "parent_check",
            "managed_by_policy",
            "overriden_by_policy",
            "created_by",
            "created_time",
            "modified_by",
            "modified_time",
        ]

    def merge_check_with_results(self, agent):
        try:
            result = PolicyCheckResult.objects.get(policy_check=self, agent=agent)
        except PolicyCheckResult.DoesNotExist:
            result = PolicyCheckResult(policy_check=self, agent=self)
            result.save()
        
        # just adding the agent result properties to the policy check and not saving
        if self.check_type == "cpuload" or self.check_type == "memcheck":
            self.alert_severity = result.alert_severity
        self.agent = agent
        self.status = result.status
        self.more_info = result.more_info
        self.last_run = result.last_run
        self.fail_count = result.fail_count
        self.outage_history = result.outage_history
        self.extra_details = result.extra_details
        self.stdout = result.stdout
        self.stderr = result.stderr
        self.retcode = result.retcode
        self.execution_time = result.execution_time
        self.history = result.history

        return self

    def save_check_result(self, data, agent) -> str:
        if self.policy:
            from checks.models import PolicyCheckResult
            check_result = PolicyCheckResult.objects.get(agent=agent, policy_check=self)
            check_result.last_run = djangotime.now()
            check_result.save(update_fields=["last_run"])
            return self.handle_check(data, check_result)
        else:
            self.last_run = djangotime.now()
            self.save(update_fields=["last_run"])
            return self.handle_check(data)

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

    def add_check_history(self, value: int, more_info: Any = None) -> None:
        CheckHistory.objects.create(check_id=self.pk, y=value, results=more_info)

    def handle_check(self, data, policy_check_result=None):
        from alerts.models import Alert

        # save reference to the check
        check = self if not policy_check_result else self.merge_check_with_results(policy_check_result.agent)

        # change self to policy_check_result if it is a policy check
        if policy_check_result:
            self = policy_check_result

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
            check.add_check_history(data["percent"])

        # diskspace checks
        elif check.check_type == "diskspace":
            if data["exists"]:
                percent_used = round(data["percent_used"])
                if check.error_threshold and (100 - percent_used) < check.error_threshold:
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
                check.add_check_history(100 - percent_used)
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
                1 if self.status == "failing" else 0, self.more_info[:60]
            )

        # windows service checks
        elif check.check_type == "winsvc":
            self.status = data["status"]
            self.more_info = data["more_info"]
            self.save(update_fields=["more_info"])

            check.add_check_history(
                1 if self.status == "failing" else 0, self.more_info[:60]
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
                "Events Found:" + str(len(self.extra_details["log"])),
            )

        # handle status
        if self.status == "failing":
            self.fail_count += 1
            self.save(update_fields=["status", "fail_count", "alert_severity"])

            if self.fail_count >= check.fails_b4_alert:
                Alert.handle_alert_failure(check)

        elif self.status == "passing":
            self.fail_count = 0
            self.save()
            # TODO handle policy check results
            if Alert.objects.filter(assigned_check=self, resolved=False).exists():
                Alert.handle_alert_resolve(check)

        return self.status

    def handle_assigned_task(self) -> None:
        for task in self.assignedtask.all():  # type: ignore
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

    def send_email(self):

        CORE = CoreSettings.objects.first()

        body: str = ""
        if self.agent:
            subject = f"{self.agent.client.name}, {self.agent.site.name}, {self.agent.hostname} - {self} Failed"
        else:
            subject = f"{self} Failed"

        if self.check_type == "diskspace":
            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            try:
                percent_used = [
                    d["percent"] for d in self.agent.disks if d["device"] == self.disk
                ][0]
                percent_free = 100 - percent_used

                body = subject + f" - Free: {percent_free}%, {text}"
            except:
                body = subject + f" - Disk {self.disk} does not exist"

        elif self.check_type == "script":

            body = (
                subject
                + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
            )

        elif self.check_type == "ping":

            body = self.more_info

        elif self.check_type == "cpuload" or self.check_type == "memory":
            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            avg = int(mean(self.history))

            if self.check_type == "cpuload":
                body = subject + f" - Average CPU utilization: {avg}%, {text}"

            elif self.check_type == "memory":
                body = subject + f" - Average memory usage: {avg}%, {text}"

        elif self.check_type == "winsvc":
            body = subject + f" - Status: {self.more_info}"

        elif self.check_type == "eventlog":

            if self.event_source and self.event_message:
                start = f"Event ID {self.event_id}, source {self.event_source}, containing string {self.event_message} "
            elif self.event_source:
                start = f"Event ID {self.event_id}, source {self.event_source} "
            elif self.event_message:
                start = (
                    f"Event ID {self.event_id}, containing string {self.event_message} "
                )
            else:
                start = f"Event ID {self.event_id} "

            body = start + f"was found in the {self.log_name} log\n\n"

            for i in self.extra_details["log"]:
                try:
                    if i["message"]:
                        body += f"{i['message']}\n"
                except:
                    continue

        CORE.send_mail(subject, body, alert_template=self.agent.alert_template)

    def send_sms(self):

        CORE = CoreSettings.objects.first()
        body: str = ""

        if self.agent:
            subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Failed"
        else:
            subject = f"{self} Failed"

        if self.check_type == "diskspace":
            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            try:
                percent_used = [
                    d["percent"] for d in self.agent.disks if d["device"] == self.disk
                ][0]
                percent_free = 100 - percent_used
                body = subject + f" - Free: {percent_free}%, {text}"
            except:
                body = subject + f" - Disk {self.disk} does not exist"

        elif self.check_type == "script":
            body = subject + f" - Return code: {self.retcode}"
        elif self.check_type == "ping":
            body = subject
        elif self.check_type == "cpuload" or self.check_type == "memory":
            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            avg = int(mean(self.history))
            if self.check_type == "cpuload":
                body = subject + f" - Average CPU utilization: {avg}%, {text}"
            elif self.check_type == "memory":
                body = subject + f" - Average memory usage: {avg}%, {text}"
        elif self.check_type == "winsvc":
            body = subject + f" - Status: {self.more_info}"
        elif self.check_type == "eventlog":
            body = subject

        CORE.send_sms(body, alert_template=self.agent.alert_template)

    def send_resolved_email(self):
        CORE = CoreSettings.objects.first()

        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        body = f"{self} is now back to normal"

        CORE.send_mail(subject, body, alert_template=self.agent.alert_template)

    def send_resolved_sms(self):
        CORE = CoreSettings.objects.first()

        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        CORE.send_sms(subject, alert_template=self.agent.alert_template)


class PolicyCheckResult(models.Model):
    objects = PermissionQuerySet.as_manager()

    agent = models.ForeignKey(
        "agents.Agent",
        related_name="policycheckhistory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    policy_check = models.ForeignKey(
        "checks.Check",
        related_name="policycheckresults",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=100, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    # for memory and cpu checks where severity changes
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
        return f"{self.agent.hostname} - {self.policy_check}" 


class CheckHistory(models.Model):
    objects = PermissionQuerySet.as_manager()

    check_id = models.PositiveIntegerField(default=0)
    x = models.DateTimeField(auto_now_add=True)
    y = models.PositiveIntegerField(null=True, blank=True, default=None)
    results = models.JSONField(null=True, blank=True)

    def __str__(self):
        return str(self.x)
