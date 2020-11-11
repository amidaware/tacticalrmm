import pytz
import random
import string
import datetime as dt

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.fields import DateTimeField
from automation.models import Policy
from logs.models import BaseAuditModel

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
        Policy,
        related_name="autotasks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    script = models.ForeignKey(
        "scripts.Script",
        null=True,
        blank=True,
        related_name="autoscript",
        on_delete=models.CASCADE,
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
    run_time_date = DateTimeField(null=True, blank=True)
    remove_if_not_scheduled = models.BooleanField(default=False)
    managed_by_policy = models.BooleanField(default=False)
    parent_task = models.PositiveIntegerField(null=True, blank=True)
    win_task_name = models.CharField(max_length=255, null=True, blank=True)
    timeout = models.PositiveIntegerField(default=120)
    retcode = models.IntegerField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, default="0.0000")
    last_run = models.DateTimeField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    sync_status = models.CharField(
        max_length=100, choices=SYNC_STATUS_CHOICES, default="notsynced"
    )

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
            ret = []
            for i in self.run_time_days:
                for j in RUN_TIME_DAY_CHOICES:
                    if i in j:
                        ret.append(j[1][0:3])

            run_time_nice = dt.datetime.strptime(
                self.run_time_minute, "%H:%M"
            ).strftime("%I:%M %p")

            if len(ret) == 7:
                return f"Every day at {run_time_nice}"
            else:
                days = ",".join(ret)
                return f"{days} at {run_time_nice}"

    @property
    def last_run_as_timezone(self):
        if self.last_run is not None and self.agent is not None:
            return self.last_run.astimezone(
                pytz.timezone(self.agent.timezone)
            ).strftime("%b-%d-%Y - %H:%M")

        return self.last_run

    @staticmethod
    def generate_task_name():
        chars = string.ascii_letters
        return "TacticalRMM_" + "".join(random.choice(chars) for i in range(35))

    @staticmethod
    def serialize(task):
        # serializes the task and returns json
        from .serializers import TaskSerializer

        return TaskSerializer(task).data

    def create_policy_task(self, agent=None, policy=None):
        from .tasks import create_win_task_schedule

        # exit if neither are set or if both are set
        if not agent and not policy or agent and policy:
            return

        assigned_check = None

        if agent and self.assigned_check:
            assigned_check = agent.agentchecks.get(parent_check=self.assigned_check.pk)
        elif policy and self.assigned_check:
            assigned_check = policy.policychecks.get(name=self.assigned_check.name)

        task = AutomatedTask.objects.create(
            agent=agent,
            policy=policy,
            managed_by_policy=bool(agent),
            parent_task=(self.pk if agent else None),
            script=self.script,
            script_args=self.script_args,
            assigned_check=assigned_check,
            name=self.name,
            run_time_days=self.run_time_days,
            run_time_minute=self.run_time_minute,
            run_time_date=self.run_time_date,
            task_type=self.task_type,
            win_task_name=self.win_task_name,
            timeout=self.timeout,
            enabled=self.enabled,
            remove_if_not_scheduled=self.remove_if_not_scheduled,
        )

        create_win_task_schedule.delay(task.pk)
