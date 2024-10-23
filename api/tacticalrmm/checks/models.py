from statistics import mean
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone as djangotime

from core.utils import get_core_settings
from logs.models import BaseAuditModel
from tacticalrmm.constants import (
    CHECKS_NON_EDITABLE_FIELDS,
    POLICY_CHECK_FIELDS_TO_COPY,
    AlertSeverity,
    CheckStatus,
    CheckType,
    EvtLogFailWhen,
    EvtLogNames,
    EvtLogTypes,
)
from tacticalrmm.helpers import has_script_actions, has_webhook
from tacticalrmm.models import PermissionQuerySet

if TYPE_CHECKING:
    from agents.models import Agent  # pragma: no cover
    from alerts.models import Alert, AlertTemplate  # pragma: no cover
    from automation.models import Policy  # pragma: no cover


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
        max_length=50, choices=CheckType.choices, default=CheckType.DISK_SPACE
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
        choices=AlertSeverity.choices,
        default=AlertSeverity.WARNING,
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
    env_vars = ArrayField(
        models.TextField(null=True, blank=True),
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
        max_length=255, choices=EvtLogNames.choices, null=True, blank=True
    )
    event_id = models.IntegerField(null=True, blank=True)
    event_id_is_wildcard = models.BooleanField(default=False)
    event_type = models.CharField(
        max_length=255, choices=EvtLogTypes.choices, null=True, blank=True
    )
    event_source = models.CharField(max_length=255, null=True, blank=True)
    event_message = models.TextField(null=True, blank=True)
    fail_when = models.CharField(
        max_length=255, choices=EvtLogFailWhen.choices, null=True, blank=True
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

        return f"{self.policy.name} - {self.readable_desc}"

    def save(self, *args, **kwargs):
        # if check is a policy check clear cache on everything
        if self.policy:
            cache.delete_many_pattern("site_*_checks")
            cache.delete_many_pattern("agent_*_checks")

        # if check is an agent check
        elif self.agent:
            cache.delete(f"agent_{self.agent.agent_id}_checks")

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # if check is a policy check clear cache on everything
        if self.policy:
            cache.delete_many_pattern("site_*_checks")
            cache.delete_many_pattern("agent_*_checks")

        # if check is an agent check
        elif self.agent:
            cache.delete(f"agent_{self.agent.agent_id}_checks")

        super().delete(*args, **kwargs)

    @property
    def readable_desc(self):
        display = self.get_check_type_display()  # type: ignore
        if self.check_type == CheckType.DISK_SPACE:
            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            return f"{display}: Drive {self.disk} - {text}"
        elif self.check_type == CheckType.PING:
            return f"{display}: {self.name}"
        elif self.check_type in (CheckType.CPU_LOAD, CheckType.MEMORY):
            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            return f"{display} - {text}"
        elif self.check_type == CheckType.WINSVC:
            return f"{display}: {self.svc_display_name}"
        elif self.check_type == CheckType.EVENT_LOG:
            return f"{display}: {self.name}"
        elif self.check_type == CheckType.SCRIPT:
            return f"{display}: {self.script.name}"

        return "n/a"

    @staticmethod
    def non_editable_fields() -> list[str]:
        return CHECKS_NON_EDITABLE_FIELDS

    def create_policy_check(self, policy: "Policy") -> None:
        check = Check.objects.create(
            policy=policy,
        )

        for task in self.assignedtasks.all():  # type: ignore
            task.create_policy_task(policy=policy, assigned_check=check)

        for field in POLICY_CHECK_FIELDS_TO_COPY:
            setattr(check, field, getattr(self, field))

        check.save()

    def should_create_alert(self, alert_template=None):
        has_check_notifications = (
            self.dashboard_alert or self.email_alert or self.text_alert
        )
        has_alert_template_notification = alert_template and (
            alert_template.check_always_alert
            or alert_template.check_always_email
            or alert_template.check_always_text
        )
        return (
            has_check_notifications
            or has_alert_template_notification
            or has_webhook(alert_template, "check")
            or has_script_actions(alert_template, "check")
        )

    def add_check_history(
        self, value: int, agent_id: str, more_info: Any = None
    ) -> None:
        CheckHistory.objects.create(
            check_id=self.pk, y=value, results=more_info, agent_id=agent_id
        )

    @staticmethod
    def serialize(check):
        # serializes the check and returns json
        from .serializers import CheckAuditSerializer

        return CheckAuditSerializer(check).data

    def is_duplicate(self, check):
        if self.check_type == CheckType.DISK_SPACE:
            return self.disk == check.disk

        elif self.check_type == CheckType.SCRIPT:
            return self.script == check.script

        elif self.check_type == CheckType.PING:
            return self.ip == check.ip

        elif self.check_type in (CheckType.CPU_LOAD, CheckType.MEMORY):
            return True

        elif self.check_type == CheckType.WINSVC:
            return self.svc_name == check.svc_name

        elif self.check_type == CheckType.EVENT_LOG:
            return [self.log_name, self.event_id] == [check.log_name, check.event_id]


class CheckResult(models.Model):
    objects = PermissionQuerySet.as_manager()

    class Meta:
        unique_together = (("agent", "assigned_check"),)

    id = models.BigAutoField(primary_key=True)
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
        max_length=100, choices=CheckStatus.choices, default=CheckStatus.PENDING
    )
    # for memory, diskspace, script, and cpu checks where severity changes
    alert_severity = models.CharField(
        max_length=15,
        choices=AlertSeverity.choices,
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
    retcode = models.BigIntegerField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, null=True, blank=True)
    # cpu and mem check history
    history = ArrayField(
        models.IntegerField(blank=True), null=True, blank=True, default=list
    )

    def __str__(self):
        return f"{self.agent.hostname} - {self.assigned_check}"

    def save(self, *args, **kwargs):
        # if check is a policy check clear cache on everything
        if not self.alert_severity and self.assigned_check.check_type in (
            CheckType.MEMORY,
            CheckType.CPU_LOAD,
            CheckType.DISK_SPACE,
            CheckType.SCRIPT,
        ):
            self.alert_severity = AlertSeverity.WARNING

        super().save(*args, **kwargs)

    @property
    def history_info(self):
        if self.assigned_check.check_type in (CheckType.CPU_LOAD, CheckType.MEMORY):
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

    def handle_check(self, data, check: "Check", agent: "Agent"):
        from alerts.models import Alert

        update_fields = []
        # cpuload or mem checks
        if check.check_type in (CheckType.CPU_LOAD, CheckType.MEMORY):
            self.history.append(data["percent"])

            if len(self.history) > 15:
                self.history = self.history[-15:]

            update_fields.extend(["history", "more_info"])

            avg = int(mean(self.history))
            txt = "Memory Usage" if check.check_type == CheckType.MEMORY else "CPU Load"
            self.more_info = f"Average {txt}: {avg}%"

            if check.error_threshold and avg > check.error_threshold:
                self.status = CheckStatus.FAILING
                self.alert_severity = AlertSeverity.ERROR
            elif check.warning_threshold and avg > check.warning_threshold:
                self.status = CheckStatus.FAILING
                self.alert_severity = AlertSeverity.WARNING
            else:
                self.status = CheckStatus.PASSING

            # add check history
            check.add_check_history(data["percent"], agent.agent_id)

        # diskspace checks
        elif check.check_type == CheckType.DISK_SPACE:
            if data["exists"]:
                percent_used = round(data["percent_used"])
                if (
                    check.error_threshold
                    and (100 - percent_used) < check.error_threshold
                ):
                    self.status = CheckStatus.FAILING
                    self.alert_severity = AlertSeverity.ERROR
                elif (
                    check.warning_threshold
                    and (100 - percent_used) < check.warning_threshold
                ):
                    self.status = CheckStatus.FAILING
                    self.alert_severity = AlertSeverity.WARNING

                else:
                    self.status = CheckStatus.PASSING

                self.more_info = data["more_info"]

                # add check history
                check.add_check_history(100 - percent_used, agent.agent_id)
            else:
                self.status = CheckStatus.FAILING
                self.alert_severity = AlertSeverity.ERROR
                self.more_info = f"Disk {check.disk} does not exist"

            update_fields.extend(["more_info"])

        # script checks
        elif check.check_type == CheckType.SCRIPT:
            self.stdout = data["stdout"]
            self.stderr = data["stderr"]
            self.retcode = data["retcode"]
            self.execution_time = "{:.4f}".format(data["runtime"])

            if data["retcode"] in check.info_return_codes:
                self.alert_severity = AlertSeverity.INFO
                self.status = CheckStatus.FAILING
            elif data["retcode"] in check.warning_return_codes:
                self.alert_severity = AlertSeverity.WARNING
                self.status = CheckStatus.FAILING
            elif data["retcode"] != 0:
                self.status = CheckStatus.FAILING
                self.alert_severity = AlertSeverity.ERROR
            else:
                self.status = CheckStatus.PASSING

            update_fields.extend(
                [
                    "stdout",
                    "stderr",
                    "retcode",
                    "execution_time",
                ]
            )

            # add check history
            check.add_check_history(
                1 if self.status == CheckStatus.FAILING else 0,
                agent.agent_id,
                {
                    "retcode": data["retcode"],
                    "stdout": data["stdout"][:60],
                    "stderr": data["stderr"][:60],
                    "execution_time": self.execution_time,
                },
            )

        # ping checks
        elif check.check_type == CheckType.PING:
            self.status = data["status"]
            self.more_info = data["output"]
            update_fields.extend(["more_info"])

            check.add_check_history(
                1 if self.status == CheckStatus.FAILING else 0,
                agent.agent_id,
                self.more_info[:60],
            )

        # windows service checks
        elif check.check_type == CheckType.WINSVC:
            self.status = data["status"]
            self.more_info = data["more_info"]
            update_fields.extend(["more_info"])

            check.add_check_history(
                1 if self.status == CheckStatus.FAILING else 0,
                agent.agent_id,
                self.more_info[:60],
            )

        elif check.check_type == CheckType.EVENT_LOG:
            log = data["log"]
            if check.fail_when == EvtLogFailWhen.CONTAINS:
                if log and len(log) >= check.number_of_events_b4_alert:
                    self.status = CheckStatus.FAILING
                else:
                    self.status = CheckStatus.PASSING

            elif check.fail_when == EvtLogFailWhen.NOT_CONTAINS:
                if log and len(log) >= check.number_of_events_b4_alert:
                    self.status = CheckStatus.PASSING
                else:
                    self.status = CheckStatus.FAILING

            self.extra_details = {"log": log}
            update_fields.extend(["extra_details"])

            check.add_check_history(
                1 if self.status == CheckStatus.FAILING else 0,
                agent.agent_id,
                "Events Found:" + str(len(self.extra_details["log"])),
            )

        self.last_run = djangotime.now()
        # handle status
        if self.status == CheckStatus.FAILING:
            self.fail_count += 1
            update_fields.extend(["status", "fail_count", "alert_severity", "last_run"])
            self.save(update_fields=update_fields)

            if self.fail_count >= check.fails_b4_alert:
                Alert.handle_alert_failure(self)

        elif self.status == CheckStatus.PASSING:
            self.fail_count = 0
            update_fields.extend(["status", "fail_count", "alert_severity", "last_run"])
            self.save(update_fields=update_fields)
            if Alert.objects.filter(
                assigned_check=check, agent=agent, resolved=False
            ).exists():
                Alert.handle_alert_resolve(self)
        else:
            update_fields.extend(["last_run"])
            self.save(update_fields=update_fields)

        return self.status

    def send_email(self):
        CORE = get_core_settings()

        body: str = ""
        if self.agent:
            subject = f"{self.agent.client.name}, {self.agent.site.name}, {self.agent.hostname} - {self} Failed"
        else:
            subject = f"{self} Failed"

        if self.assigned_check.check_type == CheckType.DISK_SPACE:
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

        elif self.assigned_check.check_type == CheckType.SCRIPT:
            body = (
                subject
                + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
            )

        elif self.assigned_check.check_type == CheckType.PING:
            body = self.more_info

        elif self.assigned_check.check_type in (CheckType.CPU_LOAD, CheckType.MEMORY):
            text = ""
            if self.assigned_check.warning_threshold:
                text += f" Warning Threshold: {self.assigned_check.warning_threshold}%"
            if self.assigned_check.error_threshold:
                text += f" Error Threshold: {self.assigned_check.error_threshold}%"

            avg = int(mean(self.history))

            if self.assigned_check.check_type == CheckType.CPU_LOAD:
                body = subject + f" - Average CPU utilization: {avg}%, {text}"

            elif self.assigned_check.check_type == CheckType.MEMORY:
                body = subject + f" - Average memory usage: {avg}%, {text}"

        elif self.assigned_check.check_type == CheckType.WINSVC:
            body = subject + f" - Status: {self.more_info}"

        elif self.assigned_check.check_type == CheckType.EVENT_LOG:
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

        if self.assigned_check.check_type == CheckType.DISK_SPACE:
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

        elif self.assigned_check.check_type == CheckType.SCRIPT:
            body = subject + f" - Return code: {self.retcode}"
        elif self.assigned_check.check_type == CheckType.PING:
            body = subject
        elif self.assigned_check.check_type in (CheckType.CPU_LOAD, CheckType.MEMORY):
            text = ""
            if self.assigned_check.warning_threshold:
                text += f" Warning Threshold: {self.assigned_check.warning_threshold}%"
            if self.assigned_check.error_threshold:
                text += f" Error Threshold: {self.assigned_check.error_threshold}%"

            avg = int(mean(self.history))
            if self.assigned_check.check_type == CheckType.CPU_LOAD:
                body = subject + f" - Average CPU utilization: {avg}%, {text}"
            elif self.assigned_check.check_type == CheckType.MEMORY:
                body = subject + f" - Average memory usage: {avg}%, {text}"
        elif self.assigned_check.check_type == CheckType.WINSVC:
            body = subject + f" - Status: {self.more_info}"
        elif self.assigned_check.check_type == CheckType.EVENT_LOG:
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

    id = models.BigAutoField(primary_key=True)
    check_id = models.PositiveIntegerField(default=0)
    agent_id = models.CharField(max_length=200, null=True, blank=True)
    x = models.DateTimeField(auto_now_add=True)
    y = models.PositiveIntegerField(null=True, blank=True, default=None)
    results = models.JSONField(null=True, blank=True)

    def __str__(self):
        return str(self.x)
