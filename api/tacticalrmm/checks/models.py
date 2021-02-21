import asyncio
import json
import os
import string
from statistics import mean
from typing import Any, List, Union

import pytz
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone as djangotime
from loguru import logger
from rest_framework.fields import JSONField

from alerts.models import SEVERITY_CHOICES
from core.models import CoreSettings
from logs.models import BaseAuditModel

from .tasks import (
    handle_check_email_alert_task,
    handle_check_sms_alert_task,
    handle_resolved_check_email_alert_task,
    handle_resolved_check_sms_alert_task,
)
from .utils import bytes2human

logger.configure(**settings.LOG_CONFIG)

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
    managed_by_policy = models.BooleanField(default=False)
    overriden_by_policy = models.BooleanField(default=False)
    parent_check = models.PositiveIntegerField(null=True, blank=True)
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

            return f"{self.get_check_type_display()}: Drive {self.disk} < {text}"
        elif self.check_type == "ping":
            return f"{self.get_check_type_display()}: {self.name}"
        elif self.check_type == "cpuload" or self.check_type == "memory":

            text = ""
            if self.warning_threshold:
                text += f" Warning Threshold: {self.warning_threshold}%"
            if self.error_threshold:
                text += f" Error Threshold: {self.error_threshold}%"

            return f"{self.get_check_type_display()} > {text}"
        elif self.check_type == "winsvc":
            return f"{self.get_check_type_display()}: {self.svc_display_name}"
        elif self.check_type == "eventlog":
            return f"{self.get_check_type_display()}: {self.name}"
        elif self.check_type == "script":
            return f"{self.get_check_type_display()}: {self.script.name}"
        else:
            return "n/a"

    @property
    def history_info(self):
        if self.check_type == "cpuload" or self.check_type == "memory":
            return ", ".join(str(f"{x}%") for x in self.history[-6:])

    @property
    def last_run_as_timezone(self):
        if self.last_run is not None and self.agent is not None:
            return self.last_run.astimezone(
                pytz.timezone(self.agent.timezone)
            ).strftime("%b-%d-%Y - %H:%M")

        return self.last_run

    @property
    def non_editable_fields(self) -> List[str]:
        return [
            "check_type",
            "status",
            "more_info",
            "last_run",
            "fail_count",
            "outage_history",
            "extra_details",
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

    def handle_alert(self) -> None:
        from alerts.models import Alert, AlertTemplate

        # return if agent is in maintenance mode
        if self.agent.maintenance_mode:
            return

        # see if agent has an alert template and use that
        alert_template: Union[AlertTemplate, None] = self.agent.get_alert_template()

        # resolve alert if it exists
        if self.status == "passing":
            if Alert.objects.filter(assigned_check=self, resolved=False).exists():
                alert = Alert.objects.get(assigned_check=self, resolved=False)
                alert.resolve()

                # check if a resolved email notification should be send
                if (
                    alert_template
                    and alert_template.check_email_on_resolved
                    and not alert.resolved_email_sent
                ):
                    handle_resolved_check_email_alert_task.delay(pk=alert.pk)

                # check if resolved text should be sent
                if (
                    alert_template
                    and alert_template.check_text_on_resolved
                    and not alert.resolved_sms_sent
                ):
                    handle_resolved_check_sms_alert_task.delay(pk=alert.pk)

                # check if resolved script should be run
                if (
                    alert_template
                    and alert_template.resolved_action
                    and not alert.resolved_action_run
                ):
                    r = self.agent.run_script(
                        scriptpk=alert_template.resolved_action.pk,
                        args=alert_template.resolved_action_args,
                        timeout=alert_template.resolved_action_timeout,
                        wait=True,
                        full=True,
                        run_on_any=True,
                    )

                    # command was successful
                    if type(r) == dict:
                        alert.resolved_action_retcode = r["retcode"]
                        alert.resolved_action_stdout = r["stdout"]
                        alert.resolved_action_stderr = r["stderr"]
                        alert.resolved_action_execution_time = "{:.4f}".format(
                            r["execution_time"]
                        )
                        alert.resolved_action_run = djangotime.now()
                        alert.save()
                    else:
                        logger.error(
                            f"Resolved action: {alert_template.action.name} failed to run on any agent for {self.agent.hostname} resolved alert for {self.check_type} check"
                        )

        elif self.fail_count >= self.fails_b4_alert:
            if not Alert.objects.filter(assigned_check=self, resolved=False).exists():

                # check if alert should be created and if not return
                if (
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
                ):
                    alert = Alert.create_check_alert(self)
                else:
                    return
            else:
                alert = Alert.objects.get(assigned_check=self, resolved=False)

                # check if alert severity changed on check and update the alert
                if self.alert_severity != alert.severity:
                    alert.severity = self.alert_severity
                    alert.save(update_fields=["severity"])

            # create alert in dashboard if enabled
            if self.dashboard_alert or (
                alert_template
                and self.alert_severity in alert_template.check_dashboard_alert_severity
                and alert_template.check_always_alert
            ):
                alert.hidden = False
                alert.save()

            # send email if enabled
            if (
                not alert.email_sent
                and self.email_alert
                or alert_template
                and self.alert_severity in alert_template.check_email_alert_severity
                and alert_template.check_always_email
            ):
                handle_check_email_alert_task.delay(
                    pk=alert.pk,
                    alert_interval=alert_template.check_periodic_alert_days
                    if alert_template
                    else None,
                )

            # send text if enabled
            if self.text_alert or (
                alert_template
                and self.alert_severity in alert_template.check_text_alert_severity
                and alert_template.check_always_text
            ):
                handle_check_sms_alert_task.delay(
                    pk=alert.pk,
                    alert_interval=alert_template.check_periodic_alert_days
                    if alert_template
                    else None,
                )

            # check if any scripts should be run
            if alert_template and alert_template.action and not alert.action_run:
                r = self.agent.run_script(
                    scriptpk=alert_template.action.pk,
                    args=alert_template.action_args,
                    timeout=alert_template.action_timeout,
                    wait=True,
                    full=True,
                    run_on_any=True,
                )

                # command was successful
                if type(r) == dict:
                    alert.action_retcode = r["retcode"]
                    alert.action_stdout = r["stdout"]
                    alert.action_stderr = r["stderr"]
                    alert.action_execution_time = "{:.4f}".format(r["execution_time"])
                    alert.action_run = djangotime.now()
                    alert.save()
                else:
                    logger.error(
                        f"Failure action: {alert_template.action.name} failed to run on any agent for {self.agent.hostname} failure alert for {self.check_type} check{r}"
                    )

    def add_check_history(self, value: int, more_info: Any = None) -> None:
        CheckHistory.objects.create(check_history=self, y=value, results=more_info)

    def handle_checkv2(self, data):

        # cpuload or mem checks
        if self.check_type == "cpuload" or self.check_type == "memory":

            self.history.append(data["percent"])

            if len(self.history) > 15:
                self.history = self.history[-15:]

            self.save(update_fields=["history"])

            avg = int(mean(self.history))

            if self.error_threshold and avg > self.error_threshold:
                self.status = "failing"
                self.alert_severity = "error"
            elif self.warning_threshold and avg > self.warning_threshold:
                self.status = "failing"
                self.alert_severity = "warning"
            else:
                self.status = "passing"

            # add check history
            self.add_check_history(data["percent"])

        # diskspace checks
        elif self.check_type == "diskspace":
            if data["exists"]:
                percent_used = round(data["percent_used"])
                total = bytes2human(data["total"])
                free = bytes2human(data["free"])

                if self.error_threshold and (100 - percent_used) < self.error_threshold:
                    self.status = "failing"
                    self.alert_severity = "error"
                elif (
                    self.warning_threshold
                    and (100 - percent_used) < self.warning_threshold
                ):
                    self.status = "failing"
                    self.alert_severity = "warning"

                else:
                    self.status = "passing"

                self.more_info = f"Total: {total}B, Free: {free}B"

                # add check history
                self.add_check_history(100 - percent_used)
            else:
                self.status = "failing"
                self.alert_severity = "error"
                self.more_info = f"Disk {self.disk} does not exist"

            self.save(update_fields=["more_info"])

        # script checks
        elif self.check_type == "script":
            self.stdout = data["stdout"]
            self.stderr = data["stderr"]
            self.retcode = data["retcode"]
            try:
                # python agent
                self.execution_time = "{:.4f}".format(data["stop"] - data["start"])
            except:
                # golang agent
                self.execution_time = "{:.4f}".format(data["runtime"])

            if data["retcode"] in self.info_return_codes:
                self.alert_severity = "info"
                self.status = "failing"
            elif data["retcode"] in self.warning_return_codes:
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
            self.add_check_history(
                1 if self.status == "failing" else 0,
                {
                    "retcode": data["retcode"],
                    "stdout": data["stdout"][:60],
                    "stderr": data["stderr"][:60],
                    "execution_time": self.execution_time,
                },
            )

        # ping checks
        elif self.check_type == "ping":
            success = ["Reply", "bytes", "time", "TTL"]
            output = data["output"]

            if data["has_stdout"]:
                if all(x in output for x in success):
                    self.status = "passing"
                else:
                    self.status = "failing"
            elif data["has_stderr"]:
                self.status = "failing"

            self.more_info = output
            self.save(update_fields=["more_info"])

            self.add_check_history(
                1 if self.status == "failing" else 0, self.more_info[:60]
            )

        # windows service checks
        elif self.check_type == "winsvc":
            svc_stat = data["status"]
            self.more_info = f"Status {svc_stat.upper()}"

            if data["exists"]:
                if svc_stat == "running":
                    self.status = "passing"
                elif svc_stat == "start_pending" and self.pass_if_start_pending:
                    self.status = "passing"
                else:
                    if self.agent and self.restart_if_stopped:
                        nats_data = {
                            "func": "winsvcaction",
                            "payload": {"name": self.svc_name, "action": "start"},
                        }
                        r = asyncio.run(self.agent.nats_cmd(nats_data, timeout=32))
                        if r == "timeout" or r == "natsdown":
                            self.status = "failing"
                        elif not r["success"] and r["errormsg"]:
                            self.status = "failing"
                        elif r["success"]:
                            self.status = "passing"
                            self.more_info = f"Status RUNNING"
                        else:
                            self.status = "failing"
                    else:
                        self.status = "failing"

            else:
                if self.pass_if_svc_not_exist:
                    self.status = "passing"
                else:
                    self.status = "failing"

                self.more_info = f"Service {self.svc_name} does not exist"

            self.save(update_fields=["more_info"])

            self.add_check_history(
                1 if self.status == "failing" else 0, self.more_info[:60]
            )

        elif self.check_type == "eventlog":
            log = []
            is_wildcard = self.event_id_is_wildcard
            eventType = self.event_type
            eventID = self.event_id
            source = self.event_source
            message = self.event_message
            r = data["log"]

            for i in r:
                if i["eventType"] == eventType:
                    if not is_wildcard and not int(i["eventID"]) == eventID:
                        continue

                    if not source and not message:
                        if is_wildcard:
                            log.append(i)
                        elif int(i["eventID"]) == eventID:
                            log.append(i)
                        continue

                    if source and message:
                        if is_wildcard:
                            if source in i["source"] and message in i["message"]:
                                log.append(i)

                        elif int(i["eventID"]) == eventID:
                            if source in i["source"] and message in i["message"]:
                                log.append(i)

                        continue

                    if source and source in i["source"]:
                        if is_wildcard:
                            log.append(i)
                        elif int(i["eventID"]) == eventID:
                            log.append(i)

                    if message and message in i["message"]:
                        if is_wildcard:
                            log.append(i)
                        elif int(i["eventID"]) == eventID:
                            log.append(i)

            if self.fail_when == "contains":
                if log:
                    self.status = "failing"
                else:
                    self.status = "passing"

            elif self.fail_when == "not_contains":
                if log:
                    self.status = "passing"
                else:
                    self.status = "failing"

            self.extra_details = {"log": log}
            self.save(update_fields=["extra_details"])

            self.add_check_history(
                1 if self.status == "failing" else 0,
                "Events Found:" + str(len(self.extra_details["log"])),
            )

        # handle status
        if self.status == "failing":
            self.fail_count += 1
            self.save(update_fields=["status", "fail_count", "alert_severity"])

        elif self.status == "passing":
            self.fail_count = 0
            self.save(update_fields=["status", "fail_count", "alert_severity"])

        self.handle_alert()

        return self.status

    @staticmethod
    def serialize(check):
        # serializes the check and returns json
        from .serializers import CheckSerializer

        return CheckSerializer(check).data

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

    def create_policy_check(self, agent=None, policy=None):

        if not agent and not policy or agent and policy:
            return

        Check.objects.create(
            agent=agent,
            policy=policy,
            managed_by_policy=bool(agent),
            parent_check=(self.pk if agent else None),
            name=self.name,
            alert_severity=self.alert_severity,
            check_type=self.check_type,
            email_alert=self.email_alert,
            dashboard_alert=self.dashboard_alert,
            text_alert=self.text_alert,
            fails_b4_alert=self.fails_b4_alert,
            extra_details=self.extra_details,
            error_threshold=self.error_threshold,
            warning_threshold=self.warning_threshold,
            disk=self.disk,
            ip=self.ip,
            script=self.script,
            script_args=self.script_args,
            timeout=self.timeout,
            info_return_codes=self.info_return_codes,
            warning_return_codes=self.warning_return_codes,
            svc_name=self.svc_name,
            svc_display_name=self.svc_display_name,
            pass_if_start_pending=self.pass_if_start_pending,
            pass_if_svc_not_exist=self.pass_if_svc_not_exist,
            restart_if_stopped=self.restart_if_stopped,
            svc_policy_mode=self.svc_policy_mode,
            log_name=self.log_name,
            event_id=self.event_id,
            event_id_is_wildcard=self.event_id_is_wildcard,
            event_type=self.event_type,
            event_source=self.event_source,
            event_message=self.event_message,
            fail_when=self.fail_when,
            search_last_days=self.search_last_days,
        )

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
        alert_template = self.agent.get_alert_template()

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

            percent_used = [
                d["percent"] for d in self.agent.disks if d["device"] == self.disk
            ][0]
            percent_free = 100 - percent_used

            body = subject + f" - Free: {percent_free}%, {text}"

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

            try:
                status = list(
                    filter(lambda x: x["name"] == self.svc_name, self.agent.services)
                )[0]["status"]
            # catch services that don't exist if policy check
            except:
                status = "Unknown"

            body = subject + f" - Status: {status.upper()}"

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

        CORE.send_mail(subject, body, alert_template=alert_template)

    def send_sms(self):

        CORE = CoreSettings.objects.first()
        alert_template = self.agent.get_alert_template()
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

            percent_used = [
                d["percent"] for d in self.agent.disks if d["device"] == self.disk
            ][0]
            percent_free = 100 - percent_used
            body = subject + f" - Free: {percent_free}%, {text}"
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
            status = list(
                filter(lambda x: x["name"] == self.svc_name, self.agent.services)
            )[0]["status"]
            body = subject + f" - Status: {status.upper()}"
        elif self.check_type == "eventlog":
            body = subject

        CORE.send_sms(body, alert_template=alert_template)

    def send_resolved_email(self):
        CORE = CoreSettings.objects.first()
        alert_template = self.agent.get_alert_template()
        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        body = f"{self} is now back to normal"

        CORE.send_mail(subject, body, alert_template=alert_template)

    def send_resolved_sms(self):
        CORE = CoreSettings.objects.first()
        alert_template = self.agent.get_alert_template()
        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        CORE.send_sms(subject, alert_template=alert_template)


class CheckHistory(models.Model):
    check_history = models.ForeignKey(
        Check,
        related_name="check_history",
        on_delete=models.CASCADE,
    )
    x = models.DateTimeField(auto_now_add=True)
    y = models.PositiveIntegerField(null=True, blank=True, default=None)
    results = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.check_history.readable_desc
