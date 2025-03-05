import asyncio
import logging
import random
import string
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.fields import DateTimeField
from django.db.models.fields.json import JSONField
from django.db.utils import DatabaseError
from django.utils import timezone as djangotime

from core.utils import get_core_settings
from logs.models import BaseAuditModel
from tacticalrmm.constants import (
    FIELDS_TRIGGER_TASK_UPDATE_AGENT,
    POLICY_TASK_FIELDS_TO_COPY,
    AgentPlat,
    AlertSeverity,
    TaskRunStatus,
    TaskStatus,
    TaskSyncStatus,
    TaskType,
)

if TYPE_CHECKING:
    from automation.models import Policy
    from alerts.models import Alert, AlertTemplate
    from agents.models import Agent
    from checks.models import Check

from tacticalrmm.helpers import has_script_actions, has_webhook
from tacticalrmm.models import PermissionQuerySet
from tacticalrmm.utils import (
    bitdays_to_string,
    bitmonthdays_to_string,
    bitmonths_to_string,
    bitweeks_to_string,
    convert_to_iso_duration,
)


def generate_task_name() -> str:
    chars = string.ascii_letters
    return "TacticalRMM_" + "".join(random.choice(chars) for i in range(35))


def default_task_supported_platforms() -> list[str]:
    return [AgentPlat.WINDOWS]


logger = logging.getLogger("trmm")


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

    # format -> [{"type": "script", "script": 1, "name": "Script Name", "timeout": 90, "script_args": [], "env_vars": []}, {"type": "cmd", "command": "whoami", "timeout": 90}]
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
        max_length=30, choices=AlertSeverity.choices, default=AlertSeverity.INFO
    )
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    dashboard_alert = models.BooleanField(default=False)

    # options sent to agent for task creation
    # general task settings
    task_type = models.CharField(
        max_length=100, choices=TaskType.choices, default=TaskType.MANUAL
    )
    win_task_name = models.CharField(
        max_length=255, unique=True, blank=True, default=generate_task_name
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

    task_supported_platforms = ArrayField(
        models.CharField(max_length=30, choices=AgentPlat.choices),
        default=default_task_supported_platforms,
    )

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
        super().save(old_model=old_task, *args, **kwargs)

        # check if fields were updated that require a sync to the agent and set status to notsynced
        if old_task:
            for field in self.fields_that_trigger_task_update_on_agent:
                if getattr(self, field) != getattr(old_task, field):
                    if self.policy:
                        TaskResult.objects.select_related("agent", "task").defer(
                            "agent__services", "agent__wmi_detail"
                        ).exclude(sync_status=TaskSyncStatus.INITIAL).filter(
                            agent__plat=AgentPlat.WINDOWS,
                            task__policy_id=self.policy.id,
                        ).update(
                            sync_status=TaskSyncStatus.NOT_SYNCED
                        )
                    else:
                        TaskResult.objects.select_related("agent", "task").defer(
                            "agent__services", "agent__wmi_detail"
                        ).filter(
                            agent=self.agent, task=self, agent__plat=AgentPlat.WINDOWS
                        ).update(
                            sync_status=TaskSyncStatus.NOT_SYNCED
                        )
                    break

    def delete(self, *args, **kwargs):
        # if task is a policy task clear cache on everything
        if self.policy:
            cache.delete_many_pattern("site_*_tasks")
            cache.delete_many_pattern("agent_*_tasks")

        super().delete(*args, **kwargs)

    @property
    def schedule(self) -> Optional[str]:
        if self.task_type == TaskType.MANUAL:
            return "Manual"
        elif self.task_type == TaskType.CHECK_FAILURE:
            return "Every time check fails"
        elif self.task_type == TaskType.RUN_ONCE:
            return f'Run once on {self.run_time_date.strftime("%m/%d/%Y %I:%M%p")}'
        elif self.task_type == TaskType.DAILY:
            run_time_nice = self.run_time_date.strftime("%I:%M%p")
            if self.daily_interval == 1:
                return f"Daily at {run_time_nice}"
            else:
                return f"Every {self.daily_interval} days at {run_time_nice}"
        elif self.task_type == TaskType.WEEKLY:
            run_time_nice = self.run_time_date.strftime("%I:%M%p")
            days = bitdays_to_string(self.run_time_bit_weekdays)
            if self.weekly_interval != 1:
                return f"{days} at {run_time_nice}"
            else:
                return f"{days} at {run_time_nice} every {self.weekly_interval} weeks"
        elif self.task_type == TaskType.MONTHLY:
            run_time_nice = self.run_time_date.strftime("%I:%M%p")
            months = bitmonths_to_string(self.monthly_months_of_year)
            days = bitmonthdays_to_string(self.monthly_days_of_month)
            return f"Runs on {months} on days {days} at {run_time_nice}"
        elif self.task_type == TaskType.MONTHLY_DOW:
            run_time_nice = self.run_time_date.strftime("%I:%M%p")
            months = bitmonths_to_string(self.monthly_months_of_year)
            weeks = bitweeks_to_string(self.monthly_weeks_of_month)
            days = bitdays_to_string(self.run_time_bit_weekdays)
            return f"Runs on {months} on {weeks} on {days} at {run_time_nice}"
        elif self.task_type == TaskType.ONBOARDING:
            return "Onboarding: Runs once on task creation."
        return None

    @property
    def fields_that_trigger_task_update_on_agent(self) -> List[str]:
        return FIELDS_TRIGGER_TASK_UPDATE_AGENT

    @staticmethod
    def serialize(task):
        # serializes the task and returns json
        from .serializers import TaskAuditSerializer

        return TaskAuditSerializer(task).data

    def create_policy_task(
        self, policy: "Policy", assigned_check: "Optional[Check]" = None
    ) -> None:
        # Copies certain properties on this task (self) to a new task and sets it to the supplied Policy
        task = AutomatedTask.objects.create(
            policy=policy,
            assigned_check=assigned_check,
        )

        for field in POLICY_TASK_FIELDS_TO_COPY:
            setattr(task, field, getattr(self, field))

        task.save()

    # agent version >= 1.8.0
    def generate_nats_task_payload(self) -> Dict[str, Any]:
        task = {
            "pk": self.pk,
            "type": "rmm",
            "name": self.win_task_name,
            "overwrite_task": True,
            "enabled": self.enabled,
            "trigger": (
                self.task_type
                if self.task_type != TaskType.CHECK_FAILURE
                else TaskType.MANUAL
            ),
            "multiple_instances": self.task_instance_policy or 0,
            "delete_expired_task_after": (
                self.remove_if_not_scheduled if self.expire_date else False
            ),
            "start_when_available": (
                self.run_asap_after_missed
                if self.task_type != TaskType.RUN_ONCE
                else True
            ),
        }

        if self.task_type in (
            TaskType.DAILY,
            TaskType.WEEKLY,
            TaskType.MONTHLY,
            TaskType.MONTHLY_DOW,
            TaskType.RUN_ONCE,
        ):
            if not self.run_time_date:
                self.run_time_date = djangotime.now()

            task["start_year"] = self.run_time_date.year
            task["start_month"] = self.run_time_date.month
            task["start_day"] = self.run_time_date.day
            task["start_hour"] = self.run_time_date.hour
            task["start_min"] = self.run_time_date.minute

            if self.expire_date:
                task["expire_year"] = self.expire_date.year
                task["expire_month"] = self.expire_date.month
                task["expire_day"] = self.expire_date.day
                task["expire_hour"] = self.expire_date.hour
                task["expire_min"] = self.expire_date.minute

            if self.random_task_delay:
                task["random_delay"] = convert_to_iso_duration(self.random_task_delay)

            if self.task_repetition_interval and self.task_repetition_duration:
                task["repetition_interval"] = convert_to_iso_duration(
                    self.task_repetition_interval
                )
                task["repetition_duration"] = convert_to_iso_duration(
                    self.task_repetition_duration
                )
                task["stop_at_duration_end"] = self.stop_task_at_duration_end

            if self.task_type == TaskType.DAILY:
                task["day_interval"] = self.daily_interval

            elif self.task_type == TaskType.WEEKLY:
                task["week_interval"] = self.weekly_interval
                task["days_of_week"] = self.run_time_bit_weekdays

            elif self.task_type == TaskType.MONTHLY:
                # check if "last day is configured"
                if self.monthly_days_of_month >= 0x80000000:
                    task["days_of_month"] = self.monthly_days_of_month - 0x80000000
                    task["run_on_last_day_of_month"] = True
                else:
                    task["days_of_month"] = self.monthly_days_of_month
                    task["run_on_last_day_of_month"] = False

                task["months_of_year"] = self.monthly_months_of_year

            elif self.task_type == TaskType.MONTHLY_DOW:
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

        if agent.is_posix:
            task_result.sync_status = TaskSyncStatus.SYNCED
            task_result.save(update_fields=["sync_status"])
            return "ok"

        nats_data = {
            "func": "schedtask",
            "schedtaskpayload": self.generate_nats_task_payload(),
        }
        logger.debug(nats_data)

        r = asyncio.run(task_result.agent.nats_cmd(nats_data, timeout=10))

        if r != "ok":
            task_result.sync_status = TaskSyncStatus.INITIAL
            task_result.save(update_fields=["sync_status"])
            logger.error(
                f"Unable to create scheduled task {self.name} on {task_result.agent.hostname}: {r}"
            )
            return "timeout"
        else:
            task_result.sync_status = TaskSyncStatus.SYNCED
            task_result.save(update_fields=["sync_status"])
            logger.info(
                f"{task_result.agent.hostname} task {self.name} was successfully created."
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

        if agent.is_posix:
            task_result.sync_status = TaskSyncStatus.SYNCED
            task_result.save(update_fields=["sync_status"])
            return "ok"

        nats_data = {
            "func": "schedtask",
            "schedtaskpayload": self.generate_nats_task_payload(),
        }
        logger.debug(nats_data)

        r = asyncio.run(task_result.agent.nats_cmd(nats_data, timeout=10))

        if r != "ok":
            task_result.sync_status = TaskSyncStatus.NOT_SYNCED
            task_result.save(update_fields=["sync_status"])
            logger.error(
                f"Unable to modify scheduled task {self.name} on {task_result.agent.hostname}: {r}"
            )
            return "timeout"
        else:
            task_result.sync_status = TaskSyncStatus.SYNCED
            task_result.save(update_fields=["sync_status"])
            logger.info(
                f"{task_result.agent.hostname} task {self.name} was successfully modified."
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

        if agent.is_posix:
            self.delete()
            return "ok"

        nats_data = {
            "func": "delschedtask",
            "schedtaskpayload": {"name": self.win_task_name},
        }
        r = asyncio.run(task_result.agent.nats_cmd(nats_data, timeout=10))

        if r != "ok" and "The system cannot find the file specified" not in r:
            task_result.sync_status = TaskSyncStatus.PENDING_DELETION

            with suppress(DatabaseError):
                task_result.save(update_fields=["sync_status"])

            logger.error(
                f"Unable to delete task {self.name} on {task_result.agent.hostname}: {r}"
            )
            return "timeout"
        else:
            self.delete()
            logger.info(f"{task_result.agent.hostname} task {self.name} was deleted.")
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
        has_autotask_notification = (
            self.dashboard_alert or self.email_alert or self.text_alert
        )
        has_alert_template_notification = alert_template and (
            alert_template.task_always_alert
            or alert_template.task_always_email
            or alert_template.task_always_text
        )
        return (
            has_autotask_notification
            or has_alert_template_notification
            or has_webhook(alert_template, "task")
            or has_script_actions(alert_template, "task")
        )


class TaskResult(models.Model):
    class Meta:
        unique_together = (("agent", "task"),)

    objects = PermissionQuerySet.as_manager()

    id = models.BigAutoField(primary_key=True)
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

    retcode = models.BigIntegerField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, default="0.0000")
    last_run = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=30, choices=TaskStatus.choices, default=TaskStatus.PENDING
    )
    sync_status = models.CharField(
        max_length=100, choices=TaskSyncStatus.choices, default=TaskSyncStatus.INITIAL
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    run_status = models.CharField(
        max_length=30, choices=TaskRunStatus.choices, null=True, blank=True
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
