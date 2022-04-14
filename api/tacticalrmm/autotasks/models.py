import asyncio
import random
import string
import pytz
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Union

from alerts.models import SEVERITY_CHOICES
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.cache import cache
from django.utils import timezone as djangotime
from django.db import models
from django.db.models.fields import DateTimeField
from django.db.models.fields.json import JSONField
from django.db.utils import DatabaseError
from logs.models import BaseAuditModel, DebugLog
from core.utils import get_core_settings

if TYPE_CHECKING:
    from automation.models import Policy
    from alerts.models import Alert, AlertTemplate
    from agents.models import Agent
    from checks.models import Check

from tacticalrmm.models import PermissionQuerySet
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

    # format -> [{"type": "script", "script": 1, "name": "Script Name", "timeout": 90, "script_args": []}, {"type": "cmd", "command": "whoami", "timeout": 90}]
    actions = JSONField(default=list)
    assigned_check = models.ForeignKey(
        "checks.Check",
        null=True,
        blank=True,
        related_name="assignedtasks",
        on_delete=models.SET_NULL,
    )
    name = models.CharField(max_length=255)
    collector_all_output = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    continue_on_error = models.BooleanField(default=True)
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
    win_task_name = models.CharField(
        max_length=255, null=True, blank=True
    )  # should be changed to unique=True
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

    # deprecated
    managed_by_policy = models.BooleanField(default=False)

    # non-database property
    task_result: "Union[TaskResult, Dict[None, None]]" = {}

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:

        # if task is a policy task clear cache on everything
        if self.policy:
            cache.delete_many_pattern("site_*_tasks")
            cache.delete_many_pattern("agent_*_tasks")

        # get old task if exists
        old_task = AutomatedTask.objects.get(pk=self.pk) if self.pk else None
        super(AutomatedTask, self).save(old_model=old_task, *args, **kwargs)

        # check if fields were updated that require a sync to the agent and set status to notsynced
        if old_task:
            for field in self.fields_that_trigger_task_update_on_agent:
                if getattr(self, field) != getattr(old_task, field):
                    if self.policy:
                        TaskResult.objects.exclude(sync_status="inital").filter(
                            task__policy_id=self.policy.id
                        ).update(sync_status="notsynced")
                    else:
                        TaskResult.objects.filter(agent=self.agent, task=self).update(
                            sync_status="notsynced"
                        )

    def delete(self, *args, **kwargs):

        # if check is a policy check clear cache on everything
        if self.policy:
            cache.delete_many_pattern("site_*_tasks")
            cache.delete_many_pattern("agent_*_tasks")

        super(AutomatedTask, self).delete(
            *args,
            **kwargs,
        )

    @property
    def schedule(self) -> Optional[str]:
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
    def generate_task_name() -> str:
        chars = string.ascii_letters
        return "TacticalRMM_" + "".join(random.choice(chars) for i in range(35))

    @staticmethod
    def serialize(task):
        # serializes the task and returns json
        from .serializers import TaskAuditSerializer

        return TaskAuditSerializer(task).data

    def create_policy_task(
        self, policy: "Policy", assigned_check: "Optional[Check]" = None
    ) -> None:
        ### Copies certain properties on this task (self) to a new task and sets it to the supplied Policy
        fields_to_copy = [
            "alert_severity",
            "email_alert",
            "text_alert",
            "dashboard_alert",
            "name",
            "actions",
            "run_time_bit_weekdays",
            "run_time_date",
            "expire_date",
            "daily_interval",
            "weekly_interval",
            "task_type",
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

        task = AutomatedTask.objects.create(
            policy=policy,
            win_task_name=AutomatedTask.generate_task_name(),
            assigned_check=assigned_check,
        )

        for field in fields_to_copy:
            setattr(task, field, getattr(self, field))

        task.save()

    # agent version >= 1.8.0
    def generate_nats_task_payload(
        self, agent: "Optional[Agent]" = None, editing: bool = False
    ) -> Dict[str, Any]:
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
            # set runonce task in future if creating and run_asap_after_missed is set
            if (
                not editing
                and self.task_type == "runonce"
                and self.run_asap_after_missed
                and agent
                and self.run_time_date
                < djangotime.now().astimezone(pytz.timezone(agent.timezone))
            ):
                self.run_time_date = (
                    djangotime.now() + djangotime.timedelta(minutes=5)
                ).astimezone(pytz.timezone(agent.timezone))

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
                if self.monthly_days_of_month >= 0x80000000:
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

    def create_task_on_agent(self, agent: "Optional[Agent]" = None) -> str:
        if self.policy and not agent:
            return "agent parameter needs to be passed with policy task"
        else:
            agent = agent if self.policy else self.agent

        try:
            task_result = TaskResult.objects.get(agent=agent, task=self)
        except TaskResult.DoesNotExist:
            task_result = TaskResult(agent=agent, task=self)
            task_result.save()

        nats_data = {
            "func": "schedtask",
            "schedtaskpayload": self.generate_nats_task_payload(agent),
        }

        r = asyncio.run(task_result.agent.nats_cmd(nats_data, timeout=5))

        if r != "ok":
            task_result.sync_status = "initial"
            task_result.save(update_fields=["sync_status"])
            DebugLog.warning(
                agent=agent,
                log_type="agent_issues",
                message=f"Unable to create scheduled task {self.name} on {task_result.agent.hostname}. It will be created when the agent checks in.",
            )
            return "timeout"
        else:
            task_result.sync_status = "synced"
            task_result.save(update_fields=["sync_status"])
            DebugLog.info(
                agent=agent,
                log_type="agent_issues",
                message=f"{task_result.agent.hostname} task {self.name} was successfully created",
            )

        return "ok"

    def modify_task_on_agent(self, agent: "Optional[Agent]" = None) -> str:
        if self.policy and not agent:
            return "agent parameter needs to be passed with policy task"
        else:
            agent = agent if self.policy else self.agent

        try:
            task_result = TaskResult.objects.get(agent=agent, task=self)
        except TaskResult.DoesNotExist:
            task_result = TaskResult(agent=agent, task=self)
            task_result.save()

        nats_data = {
            "func": "schedtask",
            "schedtaskpayload": self.generate_nats_task_payload(editing=True),
        }

        r = asyncio.run(task_result.agent.nats_cmd(nats_data, timeout=5))

        if r != "ok":
            task_result.sync_status = "notsynced"
            task_result.save(update_fields=["sync_status"])
            DebugLog.warning(
                agent=agent,
                log_type="agent_issues",
                message=f"Unable to modify scheduled task {self.name} on {task_result.agent.hostname}({task_result.agent.agent_id}). It will try again on next agent checkin",
            )
            return "timeout"
        else:
            task_result.sync_status = "synced"
            task_result.save(update_fields=["sync_status"])
            DebugLog.info(
                agent=agent,
                log_type="agent_issues",
                message=f"{task_result.agent.hostname} task {self.name} was successfully modified",
            )

        return "ok"

    def delete_task_on_agent(self, agent: "Optional[Agent]" = None) -> str:
        if self.policy and not agent:
            return "agent parameter needs to be passed with policy task"
        else:
            agent = agent if self.policy else self.agent

        try:
            task_result = TaskResult.objects.get(agent=agent, task=self)
        except TaskResult.DoesNotExist:
            task_result = TaskResult(agent=agent, task=self)
            task_result.save()

        nats_data = {
            "func": "delschedtask",
            "schedtaskpayload": {"name": self.win_task_name},
        }
        r = asyncio.run(task_result.agent.nats_cmd(nats_data, timeout=10))

        if r != "ok" and "The system cannot find the file specified" not in r:
            task_result.sync_status = "pendingdeletion"

            try:
                task_result.save(update_fields=["sync_status"])
            except DatabaseError:
                pass

            DebugLog.warning(
                agent=agent,
                log_type="agent_issues",
                message=f"{task_result.agent.hostname} task {self.name} will be deleted on next checkin",
            )
            return "timeout"
        else:
            self.delete()
            DebugLog.info(
                agent=agent,
                log_type="agent_issues",
                message=f"{task_result.agent.hostname}({task_result.agent.agent_id}) task {self.name} was deleted",
            )

        return "ok"

    def run_win_task(self, agent: "Optional[Agent]" = None) -> str:
        if self.policy and not agent:
            return "agent parameter needs to be passed with policy task"
        else:
            agent = agent if self.policy else self.agent

        try:
            task_result = TaskResult.objects.get(agent=agent, task=self)
        except TaskResult.DoesNotExist:
            task_result = TaskResult(agent=agent, task=self)
            task_result.save()

        asyncio.run(
            task_result.agent.nats_cmd(
                {"func": "runtask", "taskpk": self.pk}, wait=False
            )
        )
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


class TaskResult(models.Model):
    class Meta:
        unique_together = (("agent", "task"),)

    objects = PermissionQuerySet.as_manager()

    agent = models.ForeignKey(
        "agents.Agent",
        related_name="taskresults",
        on_delete=models.CASCADE,
    )
    task = models.ForeignKey(
        "autotasks.AutomatedTask",
        related_name="taskresults",
        on_delete=models.CASCADE,
    )

    retcode = models.IntegerField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, default="0.0000")
    last_run = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=30, choices=TASK_STATUS_CHOICES, default="pending"
    )
    sync_status = models.CharField(
        max_length=100, choices=SYNC_STATUS_CHOICES, default="initial"
    )

    def __str__(self):
        return f"{self.agent.hostname} - {self.task}"

    def get_or_create_alert_if_needed(
        self, alert_template: "Optional[AlertTemplate]"
    ) -> "Optional[Alert]":
        from alerts.models import Alert

        return Alert.create_or_return_task_alert(
            self.task,
            agent=self.agent,
            skip_create=not self.task.should_create_alert(alert_template),
        )

    def save_collector_results(self) -> None:

        agent_field = self.task.custom_field.get_or_create_field_value(self.agent)

        value = (
            self.stdout.strip()
            if self.task.collector_all_output
            else self.stdout.strip().split("\n")[-1].strip()
        )
        agent_field.save_to_field(value)

    def send_email(self):
        CORE = get_core_settings()

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
        CORE = get_core_settings()

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
        CORE = get_core_settings()

        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        body = (
            subject
            + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
        )

        CORE.send_mail(subject, body, alert_template=self.agent.alert_template)

    def send_resolved_sms(self):
        CORE = get_core_settings()
        subject = f"{self.agent.client.name}, {self.agent.site.name}, {self} Resolved"
        body = (
            subject
            + f" - Return code: {self.retcode}\nStdout:{self.stdout}\nStderr: {self.stderr}"
        )
        CORE.send_sms(body, alert_template=self.agent.alert_template)
