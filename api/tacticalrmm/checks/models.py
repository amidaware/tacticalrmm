import base64
import string
import os
import json
import pytz
import zlib
from statistics import mean

from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator

from core.models import CoreSettings
from logs.models import BaseAuditModel
from .tasks import handle_check_email_alert_task, handle_check_sms_alert_task
from .utils import bytes2human

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
    fails_b4_alert = models.PositiveIntegerField(default=1)
    fail_count = models.PositiveIntegerField(default=0)
    email_sent = models.DateTimeField(null=True, blank=True)
    text_sent = models.DateTimeField(null=True, blank=True)
    outage_history = models.JSONField(null=True, blank=True)  # store
    extra_details = models.JSONField(null=True, blank=True)

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
    script_args = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
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
            return f"{self.get_check_type_display()}: Drive {self.disk} < {self.threshold}%"
        elif self.check_type == "ping":
            return f"{self.get_check_type_display()}: {self.name}"
        elif self.check_type == "cpuload" or self.check_type == "memory":
            return f"{self.get_check_type_display()} > {self.threshold}%"
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
    def non_editable_fields(self):
        return [
            "check_type",
            "status",
            "more_info",
            "last_run",
            "fail_count",
            "email_sent",
            "text_sent",
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

    def handle_checkv2(self, data):
        # cpuload or mem checks
        if self.check_type == "cpuload" or self.check_type == "memory":

            self.history.append(data["percent"])

            if len(self.history) > 15:
                self.history = self.history[-15:]

            self.save(update_fields=["history"])

            avg = int(mean(self.history))

            if avg > self.threshold:
                self.status = "failing"
            else:
                self.status = "passing"

        # diskspace checks
        elif self.check_type == "diskspace":
            if data["exists"]:
                percent_used = round(data["percent_used"])
                total = bytes2human(data["total"])
                free = bytes2human(data["free"])

                if (100 - percent_used) < self.threshold:
                    self.status = "failing"
                else:
                    self.status = "passing"

                self.more_info = f"Total: {total}B, Free: {free}B"
            else:
                self.status = "failing"
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

            if data["retcode"] != 0:
                self.status = "failing"
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
                        r = self.agent.salt_api_cmd(
                            func="service.restart", arg=self.svc_name, timeout=45
                        )
                        if r == "timeout" or r == "error":
                            self.status = "failing"
                        elif isinstance(r, bool) and r:
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

        elif self.check_type == "eventlog":
            log = []
            is_wildcard = self.event_id_is_wildcard
            eventType = self.event_type
            eventID = self.event_id
            source = self.event_source
            message = self.event_message

            r = json.loads(zlib.decompress(base64.b64decode(data["log"])))

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

        # handle status
        if self.status == "failing":
            self.fail_count += 1
            self.save(update_fields=["status", "fail_count"])

        elif self.status == "passing":
            if self.fail_count != 0:
                self.fail_count = 0
                self.save(update_fields=["status", "fail_count"])
            else:
                self.save(update_fields=["status"])

        if self.fail_count >= self.fails_b4_alert:
            if self.email_alert:
                handle_check_email_alert_task.delay(self.pk)
            if self.text_alert:
                handle_check_sms_alert_task.delay(self.pk)

        return self.status

    def handle_check(self, data):
        if self.check_type != "cpuload" and self.check_type != "memory":

            if data["status"] == "passing" and self.fail_count != 0:
                self.fail_count = 0
                self.save(update_fields=["fail_count"])

            elif data["status"] == "failing":
                self.fail_count += 1
                self.save(update_fields=["fail_count"])

        else:
            self.history.append(data["percent"])

            if len(self.history) > 15:
                self.history = self.history[-15:]

            self.save(update_fields=["history"])

            avg = int(mean(self.history))

            if avg > self.threshold:
                self.status = "failing"
                self.fail_count += 1
                self.save(update_fields=["status", "fail_count"])
            else:
                self.status = "passing"
                if self.fail_count != 0:
                    self.fail_count = 0
                    self.save(update_fields=["status", "fail_count"])
                else:
                    self.save(update_fields=["status"])

        if self.email_alert and self.fail_count >= self.fails_b4_alert:
            handle_check_email_alert_task.delay(self.pk)

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
            check_type=self.check_type,
            email_alert=self.email_alert,
            text_alert=self.text_alert,
            fails_b4_alert=self.fails_b4_alert,
            extra_details=self.extra_details,
            threshold=self.threshold,
            disk=self.disk,
            ip=self.ip,
            script=self.script,
            script_args=self.script_args,
            timeout=self.timeout,
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

        if self.agent:
            subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Failed"
        else:
            subject = f"{self} Failed"

        if self.check_type == "diskspace":
            percent_used = [
                d["percent"] for d in self.agent.disks if d["device"] == self.disk
            ][0]
            percent_free = 100 - percent_used

            body = subject + f" - Free: {percent_free}%, Threshold: {self.threshold}%"

        elif self.check_type == "script":

            body = (
                subject
                + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
            )

        elif self.check_type == "ping":

            body = self.more_info

        elif self.check_type == "cpuload" or self.check_type == "memory":

            avg = int(mean(self.history))

            if self.check_type == "cpuload":
                body = (
                    subject
                    + f" - Average CPU utilization: {avg}%, Threshold: {self.threshold}%"
                )

            elif self.check_type == "memory":
                body = (
                    subject
                    + f" - Average memory usage: {avg}%, Threshold: {self.threshold}%"
                )

        elif self.check_type == "winsvc":

            status = list(
                filter(lambda x: x["name"] == self.svc_name, self.agent.services)
            )[0]["status"]

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

        CORE.send_mail(subject, body)

    def send_sms(self):

        CORE = CoreSettings.objects.first()

        if self.agent:
            subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Failed"
        else:
            subject = f"{self} Failed"

        if self.check_type == "diskspace":
            percent_used = [
                d["percent"] for d in self.agent.disks if d["device"] == self.disk
            ][0]
            percent_free = 100 - percent_used
            body = subject + f" - Free: {percent_free}%, Threshold: {self.threshold}%"
        elif self.check_type == "script":
            body = subject + f" - Return code: {self.retcode}"
        elif self.check_type == "ping":
            body = subject
        elif self.check_type == "cpuload" or self.check_type == "memory":
            avg = int(mean(self.history))
            if self.check_type == "cpuload":
                body = (
                    subject
                    + f" - Average CPU utilization: {avg}%, Threshold: {self.threshold}%"
                )
            elif self.check_type == "memory":
                body = (
                    subject
                    + f" - Average memory usage: {avg}%, Threshold: {self.threshold}%"
                )
        elif self.check_type == "winsvc":
            status = list(
                filter(lambda x: x["name"] == self.svc_name, self.agent.services)
            )[0]["status"]
            body = subject + f" - Status: {status.upper()}"
        elif self.check_type == "eventlog":
            body = subject

        CORE.send_sms(body)
