import asyncio
import datetime as dt
import random
import string
from typing import List

import pytz
from alerts.models import SEVERITY_CHOICES
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.fields import DateTimeField
from django.db.utils import DatabaseError
from django.utils import timezone as djangotime
from logs.models import BaseAuditModel
from loguru import logger
from packaging import version as pyver
from tacticalrmm.utils import bitdays_to_string

logger.configure(**settings.LOG_CONFIG)

RUN_TIME_DAY_CHOICES = [
    (0, "Monday"),
    (1, "Tuesday"),
    (2, "Wednesday"),
    (3, "Thursday"),
    (4, "Friday"),
    (5, "Saturday"),
    (6, "Sunday"),
]

TASK_TYPE_CHOICES = [
    ("scheduled", "Scheduled"),
    ("checkfailure", "On Check Failure"),
    ("manual", "Manual"),
    ("runonce", "Run Once"),
]

SYNC_STATUS_CHOICES = [
    ("synced", "Synced With Agent"),
    ("notsynced", "Waiting On Agent Checkin"),
    ("pendingdeletion", "Pending Deletion on Agent"),
    ("initial", "Initial Task Sync"),
]

TASK_STATUS_CHOICES = [
    ("passing", "Passing"),
    ("failing", "Failing"),
    ("pending", "Pending"),
]


class AutomatedTask(BaseAuditModel):
    agent = models.ForeignKey(
        "agents.Agent",
        related_name="autotasks",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    policy = models.ForeignKey(
        "automation.Policy",
        related_name="autotasks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    custom_field = models.ForeignKey(
        "core.CustomField",
        related_name="autotasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    script = models.ForeignKey(
        "scripts.Script",
        null=True,
        blank=True,
        related_name="autoscript",
        on_delete=models.SET_NULL,
    )
    script_args = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    assigned_check = models.ForeignKey(
        "checks.Check",
        null=True,
        blank=True,
        related_name="assignedtask",
        on_delete=models.SET_NULL,
    )
    name = models.CharField(max_length=255)
    run_time_bit_weekdays = models.IntegerField(null=True, blank=True)
    # run_time_days is deprecated, use bit weekdays
    run_time_days = ArrayField(
        models.IntegerField(choices=RUN_TIME_DAY_CHOICES, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    run_time_minute = models.CharField(max_length=5, null=True, blank=True)
    task_type = models.CharField(
        max_length=100, choices=TASK_TYPE_CHOICES, default="manual"
    )
    collector_all_output = models.BooleanField(default=False)
    run_time_date = DateTimeField(null=True, blank=True)
    remove_if_not_scheduled = models.BooleanField(default=False)
    run_asap_after_missed = models.BooleanField(default=False)  # added in agent v1.4.7
    managed_by_policy = models.BooleanField(default=False)
    parent_task = models.PositiveIntegerField(null=True, blank=True)
    win_task_name = models.CharField(max_length=255, null=True, blank=True)
    timeout = models.PositiveIntegerField(default=120)
    retvalue = models.TextField(null=True, blank=True)
    retcode = models.IntegerField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, default="0.0000")
    last_run = models.DateTimeField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    status = models.CharField(
        max_length=30, choices=TASK_STATUS_CHOICES, default="pending"
    )
    sync_status = models.CharField(
        max_length=100, choices=SYNC_STATUS_CHOICES, default="initial"
    )
    alert_severity = models.CharField(
        max_length=30, choices=SEVERITY_CHOICES, default="info"
    )
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    dashboard_alert = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def schedule(self):
        if self.task_type == "manual":
            return "Manual"
        elif self.task_type == "checkfailure":
            return "Every time check fails"
        elif self.task_type == "runonce":
            return f'Run once on {self.run_time_date.strftime("%m/%d/%Y %I:%M%p")}'
        elif self.task_type == "scheduled":
            run_time_nice = dt.datetime.strptime(
                self.run_time_minute, "%H:%M"
            ).strftime("%I:%M %p")

            days = bitdays_to_string(self.run_time_bit_weekdays)
            return f"{days} at {run_time_nice}"

    @property
    def last_run_as_timezone(self):
        if self.last_run is not None and self.agent is not None:
            return self.last_run.astimezone(
                pytz.timezone(self.agent.timezone)
            ).strftime("%b-%d-%Y - %H:%M")

        return self.last_run

    # These fields will be duplicated on the agent tasks that are managed by a policy
    @property
    def policy_fields_to_copy(self) -> List[str]:
        return [
            "alert_severity",
            "email_alert",
            "text_alert",
            "dashboard_alert",
            "script",
            "script_args",
            "assigned_check",
            "name",
            "run_time_days",
            "run_time_minute",
            "run_time_bit_weekdays",
            "run_time_date",
            "task_type",
            "win_task_name",
            "timeout",
            "enabled",
            "remove_if_not_scheduled",
            "run_asap_after_missed",
            "custom_field",
            "collector_all_output",
        ]

    @staticmethod
    def generate_task_name():
        chars = string.ascii_letters
        return "TacticalRMM_" + "".join(random.choice(chars) for i in range(35))

    @staticmethod
    def serialize(task):
        # serializes the task and returns json
        from .serializers import TaskSerializer

        return TaskSerializer(task).data

    def create_policy_task(self, agent=None, policy=None, assigned_check=None):

        # if policy is present, then this task is being copied to another policy
        # if agent is present, then this task is being created on an agent from a policy
        # exit if neither are set or if both are set
        # also exit if assigned_check is set because this task will be created when the check is
        if (
            (not agent and not policy)
            or (agent and policy)
            or (self.assigned_check and not assigned_check)
        ):
            return

        task = AutomatedTask.objects.create(
            agent=agent,
            policy=policy,
            managed_by_policy=bool(agent),
            parent_task=(self.pk if agent else None),
            assigned_check=assigned_check,
        )

        for field in self.policy_fields_to_copy:
            if field != "assigned_check":
                setattr(task, field, getattr(self, field))

        task.save()

        if agent:
            task.create_task_on_agent()

    def create_task_on_agent(self):
        from agents.models import Agent

        agent = (
            Agent.objects.filter(pk=self.agent.pk)
            .only("pk", "version", "hostname", "agent_id")
            .first()
        )

        if self.task_type == "scheduled":
            nats_data = {
                "func": "schedtask",
                "schedtaskpayload": {
                    "type": "rmm",
                    "trigger": "weekly",
                    "weekdays": self.run_time_bit_weekdays,
                    "pk": self.pk,
                    "name": self.win_task_name,
                    "hour": dt.datetime.strptime(self.run_time_minute, "%H:%M").hour,
                    "min": dt.datetime.strptime(self.run_time_minute, "%H:%M").minute,
                },
            }

        elif self.task_type == "runonce":
            # check if scheduled time is in the past
            agent_tz = pytz.timezone(agent.timezone)
            task_time_utc = self.run_time_date.replace(tzinfo=agent_tz).astimezone(
                pytz.utc
            )
            now = djangotime.now()
            if task_time_utc < now:
                self.run_time_date = now.astimezone(agent_tz).replace(
                    tzinfo=pytz.utc
                ) + djangotime.timedelta(minutes=5)
                self.save(update_fields=["run_time_date"])

            nats_data = {
                "func": "schedtask",
                "schedtaskpayload": {
                    "type": "rmm",
                    "trigger": "once",
                    "pk": self.pk,
                    "name": self.win_task_name,
                    "year": int(dt.datetime.strftime(self.run_time_date, "%Y")),
                    "month": dt.datetime.strftime(self.run_time_date, "%B"),
                    "day": int(dt.datetime.strftime(self.run_time_date, "%d")),
                    "hour": int(dt.datetime.strftime(self.run_time_date, "%H")),
                    "min": int(dt.datetime.strftime(self.run_time_date, "%M")),
                },
            }

            if self.run_asap_after_missed and pyver.parse(agent.version) >= pyver.parse(
                "1.4.7"
            ):
                nats_data["schedtaskpayload"]["run_asap_after_missed"] = True

            if self.remove_if_not_scheduled:
                nats_data["schedtaskpayload"]["deleteafter"] = True

        elif self.task_type == "checkfailure" or self.task_type == "manual":
            nats_data = {
                "func": "schedtask",
                "schedtaskpayload": {
                    "type": "rmm",
                    "trigger": "manual",
                    "pk": self.pk,
                    "name": self.win_task_name,
                },
            }
        else:
            return "error"

        r = asyncio.run(agent.nats_cmd(nats_data, timeout=5))

        if r != "ok":
            self.sync_status = "initial"
            self.save(update_fields=["sync_status"])
            logger.warning(
                f"Unable to create scheduled task {self.name} on {agent.hostname}. It will be created when the agent checks in."
            )
            return "timeout"
        else:
            self.sync_status = "synced"
            self.save(update_fields=["sync_status"])
            logger.info(f"{agent.hostname} task {self.name} was successfully created")

        return "ok"

    def modify_task_on_agent(self):
        from agents.models import Agent

        agent = (
            Agent.objects.filter(pk=self.agent.pk)
            .only("pk", "version", "hostname", "agent_id")
            .first()
        )

        nats_data = {
            "func": "enableschedtask",
            "schedtaskpayload": {
                "name": self.win_task_name,
                "enabled": self.enabled,
            },
        }
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=5))

        if r != "ok":
            self.sync_status = "notsynced"
            self.save(update_fields=["sync_status"])
            logger.warning(
                f"Unable to modify scheduled task {self.name} on {agent.hostname}. It will try again on next agent checkin"
            )
            return "timeout"
        else:
            self.sync_status = "synced"
            self.save(update_fields=["sync_status"])
            logger.info(f"{agent.hostname} task {self.name} was successfully modified")

        return "ok"

    def delete_task_on_agent(self):
        from agents.models import Agent

        agent = (
            Agent.objects.filter(pk=self.agent.pk)
            .only("pk", "version", "hostname", "agent_id")
            .first()
        )

        nats_data = {
            "func": "delschedtask",
            "schedtaskpayload": {"name": self.win_task_name},
        }
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=10))

        if r != "ok" and "The system cannot find the file specified" not in r:
            self.sync_status = "pendingdeletion"

            try:
                self.save(update_fields=["sync_status"])
            except DatabaseError:
                pass

            logger.warning(
                f"{agent.hostname} task {self.name} will be deleted on next checkin"
            )
            return "timeout"
        else:
            self.delete()
            logger.info(f"{agent.hostname} task {self.name} was deleted")

        return "ok"

    def run_win_task(self):
        from agents.models import Agent

        agent = (
            Agent.objects.filter(pk=self.agent.pk)
            .only("pk", "version", "hostname", "agent_id")
            .first()
        )

        asyncio.run(agent.nats_cmd({"func": "runtask", "taskpk": self.pk}, wait=False))
        return "ok"

    def should_create_alert(self, alert_template=None):
        return (
            self.dashboard_alert
            or self.email_alert
            or self.text_alert
            or (
                alert_template
                and (
                    alert_template.task_always_alert
                    or alert_template.task_always_email
                    or alert_template.task_always_text
                )
            )
        )

    def send_email(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        # Format of Email sent when Task has email alert
        if self.agent:
            subject = f"{self.agent.client.name}, {self.agent.site.name}, {self.agent.hostname} - {self} Failed"
        else:
            subject = f"{self} Failed"

        body = (
            subject
            + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
        )

        CORE.send_mail(subject, body, self.agent.alert_template)

    def send_sms(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        # Format of SMS sent when Task has SMS alert
        if self.agent:
            subject = f"{self.agent.client.name}, {self.agent.site.name}, {self.agent.hostname} - {self} Failed"
        else:
            subject = f"{self} Failed"

        body = (
            subject
            + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
        )

        CORE.send_sms(body, alert_template=self.agent.alert_template)

    def send_resolved_email(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        body = (
            subject
            + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
        )

        CORE.send_mail(subject, body, alert_template=self.agent.alert_template)

    def send_resolved_sms(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        body = (
            subject
            + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
        )
        CORE.send_sms(body, alert_template=self.agent.alert_template)
