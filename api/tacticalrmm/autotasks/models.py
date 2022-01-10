import asyncio
import datetime as dt
import random
import string
from typing import List
from django.db.models.fields.json import JSONField

import pytz
from alerts.models import SEVERITY_CHOICES
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.fields import DateTimeField
from django.db.utils import DatabaseError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone as djangotime
from logs.models import BaseAuditModel, DebugLog
from tacticalrmm.models import PermissionQuerySet
from packaging import version as pyver
from tacticalrmm.utils import (
    bitdays_to_string,
    bitmonthdays_to_string,
    bitmonths_to_string,
    bitweeks_to_string,
    convert_to_iso_duration,
)

TASK_TYPE_CHOICES = [
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("monthlydow", "Monthly Day of Week"),
    ("checkfailure", "On Check Failure"),
    ("manual", "Manual"),
    ("runonce", "Run Once"),
    ("scheduled", "Scheduled"),  # deprecated
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
    objects = PermissionQuerySet.as_manager()

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

    # deprecated
    script = models.ForeignKey(
        "scripts.Script",
        null=True,
        blank=True,
        related_name="autoscript",
        on_delete=models.SET_NULL,
    )
    # deprecated
    script_args = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    # deprecated
    timeout = models.PositiveIntegerField(blank=True, default=120)

    # format -> {"actions": [{"type": "script", "script": 1, "name": "Script Name", "timeout": 90, "script_args": []}, {"type": "cmd", "command": "whoami", "timeout": 90}]}
    actions = JSONField(default=list)
    assigned_check = models.ForeignKey(
        "checks.Check",
        null=True,
        blank=True,
        related_name="assignedtask",
        on_delete=models.SET_NULL,
    )
    name = models.CharField(max_length=255)
    collector_all_output = models.BooleanField(default=False)
    managed_by_policy = models.BooleanField(default=False)
    parent_task = models.PositiveIntegerField(null=True, blank=True)
    retvalue = models.TextField(null=True, blank=True)
    retcode = models.IntegerField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, default="0.0000")
    last_run = models.DateTimeField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    continue_on_error = models.BooleanField(default=True)
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

    # options sent to agent for task creation
    # general task settings
    task_type = models.CharField(
        max_length=100, choices=TASK_TYPE_CHOICES, default="manual"
    )
    win_task_name = models.CharField(max_length=255, null=True, blank=True)
    run_time_date = DateTimeField(null=True, blank=True)
    expire_date = DateTimeField(null=True, blank=True)

    # daily
    daily_interval = models.PositiveSmallIntegerField(
        blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(255)]
    )

    # weekly
    run_time_bit_weekdays = models.IntegerField(null=True, blank=True)
    weekly_interval = models.PositiveSmallIntegerField(
        blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(52)]
    )
    run_time_minute = models.CharField(
        max_length=5, null=True, blank=True
    )  # deprecated

    # monthly
    monthly_days_of_month = models.PositiveBigIntegerField(blank=True, null=True)
    monthly_months_of_year = models.PositiveIntegerField(blank=True, null=True)

    # monthly days of week
    monthly_weeks_of_month = models.PositiveSmallIntegerField(blank=True, null=True)

    # additional task settings
    task_repetition_duration = models.CharField(max_length=10, null=True, blank=True)
    task_repetition_interval = models.CharField(max_length=10, null=True, blank=True)
    stop_task_at_duration_end = models.BooleanField(blank=True, default=False)
    random_task_delay = models.CharField(max_length=10, null=True, blank=True)
    remove_if_not_scheduled = models.BooleanField(default=False)
    run_asap_after_missed = models.BooleanField(default=False)  # added in agent v1.4.7
    task_instance_policy = models.PositiveSmallIntegerField(blank=True, default=1)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from autotasks.tasks import modify_win_task
        from automation.tasks import update_policy_autotasks_fields_task

        # get old agent if exists
        old_task = AutomatedTask.objects.get(pk=self.pk) if self.pk else None
        super(AutomatedTask, self).save(old_model=old_task, *args, **kwargs)

        # check if fields were updated that require a sync to the agent
        update_agent = False
        if old_task:
            for field in self.fields_that_trigger_task_update_on_agent:
                if getattr(self, field) != getattr(old_task, field):
                    update_agent = True
                    break

        # check if automated task was enabled/disabled and send celery task
        if old_task and old_task.agent and update_agent:
            modify_win_task.delay(pk=self.pk)

        # check if policy task was edited and then check if it was a field worth copying to rest of agent tasks
        elif old_task and old_task.policy:
            if update_agent:
                update_policy_autotasks_fields_task.delay(
                    task=self.pk, update_agent=update_agent
                )
            else:
                for field in self.policy_fields_to_copy:
                    if getattr(self, field) != getattr(old_task, field):
                        update_policy_autotasks_fields_task.delay(task=self.pk)
                        break

    @property
    def schedule(self):
        if self.task_type == "manual":
            return "Manual"
        elif self.task_type == "checkfailure":
            return "Every time check fails"
        elif self.task_type == "runonce":
            return f'Run once on {self.run_time_date.strftime("%m/%d/%Y %I:%M%p")}'
        elif self.task_type == "daily":
            run_time_nice = self.run_time_date.strftime("%I:%M%p")
            if self.daily_interval == 1:
                return f"Daily at {run_time_nice}"
            else:
                return f"Every {self.daily_interval} days at {run_time_nice}"
        elif self.task_type == "weekly":
            run_time_nice = self.run_time_date.strftime("%I:%M%p")
            days = bitdays_to_string(self.run_time_bit_weekdays)
            if self.weekly_interval != 1:
                return f"{days} at {run_time_nice}"
            else:
                return f"{days} at {run_time_nice} every {self.weekly_interval} weeks"
        elif self.task_type == "monthly":
            run_time_nice = self.run_time_date.strftime("%I:%M%p")
            months = bitmonths_to_string(self.monthly_months_of_year)
            days = bitmonthdays_to_string(self.monthly_days_of_month)
            return f"Runs on {months} on days {days} at {run_time_nice}"
        elif self.task_type == "monthlydow":
            run_time_nice = self.run_time_date.strftime("%I:%M%p")
            months = bitmonths_to_string(self.monthly_months_of_year)
            weeks = bitweeks_to_string(self.monthly_weeks_of_month)
            days = bitdays_to_string(self.run_time_bit_weekdays)
            return f"Runs on {months} on {weeks} on {days} at {run_time_nice}"

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
            "assigned_check",
            "name",
            "actions",
            "run_time_bit_weekdays",
            "run_time_date",
            "expire_date",
            "daily_interval",
            "weekly_interval",
            "task_type",
            "win_task_name",
            "enabled",
            "remove_if_not_scheduled",
            "run_asap_after_missed",
            "custom_field",
            "collector_all_output",
            "monthly_days_of_month",
            "monthly_months_of_year",
            "monthly_weeks_of_month",
            "task_repetition_duration",
            "task_repetition_interval",
            "stop_task_at_duration_end",
            "random_task_delay",
            "run_asap_after_missed",
            "task_instance_policy",
            "continue_on_error",
        ]

    @property
    def fields_that_trigger_task_update_on_agent(self) -> List[str]:
        return [
            "run_time_bit_weekdays",
            "run_time_date",
            "expire_date",
            "daily_interval",
            "weekly_interval",
            "enabled",
            "remove_if_not_scheduled",
            "run_asap_after_missed",
            "monthly_days_of_month",
            "monthly_months_of_year",
            "monthly_weeks_of_month",
            "task_repetition_duration",
            "task_repetition_interval",
            "stop_task_at_duration_end",
            "random_task_delay",
            "run_asap_after_missed",
            "task_instance_policy",
        ]

    @staticmethod
    def generate_task_name():
        chars = string.ascii_letters
        return "TacticalRMM_" + "".join(random.choice(chars) for i in range(35))

    @staticmethod
    def serialize(task):
        # serializes the task and returns json
        from .serializers import TaskAuditSerializer

        return TaskAuditSerializer(task).data

    def create_policy_task(self, agent=None, policy=None, assigned_check=None):

        # added to allow new policy tasks to be assigned to check only when the agent check exists already
        if (
            self.assigned_check
            and agent
            and agent.agentchecks.filter(parent_check=self.assigned_check.id).exists()
        ):
            assigned_check = agent.agentchecks.get(parent_check=self.assigned_check.id)

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

    # agent version >= 1.7.3
    def generate_nats_task_payload(self, editing=False):
        task = {
            "pk": self.pk,
            "type": "rmm",
            "name": self.win_task_name,
            "overwrite_task": editing,
            "enabled": self.enabled,
            "trigger": self.task_type if self.task_type != "checkfailure" else "manual",
            "multiple_instances": self.task_instance_policy
            if self.task_instance_policy
            else 0,
            "delete_expired_task_after": self.remove_if_not_scheduled
            if self.expire_date
            else False,
            "start_when_available": self.run_asap_after_missed
            if self.task_type != "runonce"
            else True,
        }

        if self.task_type in ["runonce", "daily", "weekly", "monthly", "monthlydow"]:

            task["start_year"] = int(self.run_time_date.strftime("%Y"))
            task["start_month"] = int(self.run_time_date.strftime("%-m"))
            task["start_day"] = int(self.run_time_date.strftime("%-d"))
            task["start_hour"] = int(self.run_time_date.strftime("%-H"))
            task["start_min"] = int(self.run_time_date.strftime("%-M"))

            if self.expire_date:
                task["expire_year"] = int(self.expire_date.strftime("%Y"))
                task["expire_month"] = int(self.expire_date.strftime("%-m"))
                task["expire_day"] = int(self.expire_date.strftime("%-d"))
                task["expire_hour"] = int(self.expire_date.strftime("%-H"))
                task["expire_min"] = int(self.expire_date.strftime("%-M"))

            if self.random_task_delay:
                task["random_delay"] = convert_to_iso_duration(self.random_task_delay)

            if self.task_repetition_interval:
                task["repetition_interval"] = convert_to_iso_duration(
                    self.task_repetition_interval
                )
                task["repetition_duration"] = convert_to_iso_duration(
                    self.task_repetition_duration
                )
                task["stop_at_duration_end"] = self.stop_task_at_duration_end

            if self.task_type == "daily":
                task["day_interval"] = self.daily_interval

            elif self.task_type == "weekly":
                task["week_interval"] = self.weekly_interval
                task["days_of_week"] = self.run_time_bit_weekdays

            elif self.task_type == "monthly":

                # check if "last day is configured"
                if self.monthly_days_of_month > 0x80000000:
                    task["days_of_month"] = self.monthly_days_of_month - 0x80000000
                    task["run_on_last_day_of_month"] = True
                else:
                    task["days_of_month"] = self.monthly_days_of_month
                    task["run_on_last_day_of_month"] = False

                task["months_of_year"] = self.monthly_months_of_year

            elif self.task_type == "monthlydow":
                task["days_of_week"] = self.run_time_bit_weekdays
                task["months_of_year"] = self.monthly_months_of_year
                task["weeks_of_month"] = self.monthly_weeks_of_month

        return task

    def create_task_on_agent(self):
        from agents.models import Agent

        agent = (
            Agent.objects.filter(pk=self.agent.pk)
            .only("pk", "version", "hostname", "agent_id")
            .get()
        )

        if pyver.parse(agent.version) >= pyver.parse("1.7.3"):
            nats_data = {
                "func": "schedtask",
                "schedtaskpayload": self.generate_nats_task_payload(),
            }
        else:

            if self.task_type == "scheduled":
                nats_data = {
                    "func": "schedtask",
                    "schedtaskpayload": {
                        "type": "rmm",
                        "trigger": "weekly",
                        "weekdays": self.run_time_bit_weekdays,
                        "pk": self.pk,
                        "name": self.win_task_name,
                        "hour": dt.datetime.strptime(
                            self.run_time_minute, "%H:%M"
                        ).hour,
                        "min": dt.datetime.strptime(
                            self.run_time_minute, "%H:%M"
                        ).minute,
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

                if self.run_asap_after_missed and pyver.parse(
                    agent.version
                ) >= pyver.parse("1.4.7"):
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
            DebugLog.warning(
                agent=agent,
                log_type="agent_issues",
                message=f"Unable to create scheduled task {self.name} on {agent.hostname}. It will be created when the agent checks in.",
            )
            return "timeout"
        else:
            self.sync_status = "synced"
            self.save(update_fields=["sync_status"])
            DebugLog.info(
                agent=agent,
                log_type="agent_issues",
                message=f"{agent.hostname} task {self.name} was successfully created",
            )

        return "ok"

    def modify_task_on_agent(self):
        from agents.models import Agent

        agent = (
            Agent.objects.filter(pk=self.agent.pk)
            .only("pk", "version", "hostname", "agent_id")
            .get()
        )

        if pyver.parse(agent.version) >= pyver.parse("1.7.3"):
            nats_data = {
                "func": "schedtask",
                "schedtaskpayload": self.generate_nats_task_payload(editing=True),
            }
        else:
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
            DebugLog.warning(
                agent=agent,
                log_type="agent_issues",
                message=f"Unable to modify scheduled task {self.name} on {agent.hostname}({agent.pk}). It will try again on next agent checkin",
            )
            return "timeout"
        else:
            self.sync_status = "synced"
            self.save(update_fields=["sync_status"])
            DebugLog.info(
                agent=agent,
                log_type="agent_issues",
                message=f"{agent.hostname} task {self.name} was successfully modified",
            )

        return "ok"

    def delete_task_on_agent(self):
        from agents.models import Agent

        agent = (
            Agent.objects.filter(pk=self.agent.pk)
            .only("pk", "version", "hostname", "agent_id")
            .get()
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

            DebugLog.warning(
                agent=agent,
                log_type="agent_issues",
                message=f"{agent.hostname} task {self.name} will be deleted on next checkin",
            )
            return "timeout"
        else:
            self.delete()
            DebugLog.info(
                agent=agent,
                log_type="agent_issues",
                message=f"{agent.hostname}({agent.pk}) task {self.name} was deleted",
            )

        return "ok"

    def run_win_task(self):
        from agents.models import Agent

        agent = (
            Agent.objects.filter(pk=self.agent.pk)
            .only("pk", "version", "hostname", "agent_id")
            .get()
        )

        asyncio.run(agent.nats_cmd({"func": "runtask", "taskpk": self.pk}, wait=False))
        return "ok"

    def save_collector_results(self):

        agent_field = self.custom_field.get_or_create_field_value(self.agent)

        value = (
            self.stdout.strip()
            if self.collector_all_output
            else self.stdout.strip().split("\n")[-1].strip()
        )
        agent_field.save_to_field(value)

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

        CORE.send_mail(subject, body, self.agent.alert_template)  # type: ignore

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

        CORE.send_sms(body, alert_template=self.agent.alert_template)  # type: ignore

    def send_resolved_email(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        body = (
            subject
            + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
        )

        CORE.send_mail(subject, body, alert_template=self.agent.alert_template)  # type: ignore

    def send_resolved_sms(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        body = (
            subject
            + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
        )
        CORE.send_sms(body, alert_template=self.agent.alert_template)  # type: ignore
