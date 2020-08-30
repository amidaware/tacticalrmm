import random
import string
import datetime as dt

from django.db import models
from django.contrib.postgres.fields import ArrayField
from agents.models import Agent
from automation.models import Policy

import autotasks

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
]


class AutomatedTask(models.Model):
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

    def __str__(self):
        return self.name

    @property
    def schedule(self):
        if self.task_type == "manual":
            return "Manual"
        elif self.task_type == "checkfailure":
            return "Every time check fails"
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

    @staticmethod
    def generate_task_name():
        chars = string.ascii_letters
        return "TacticalRMM_" + "".join(random.choice(chars) for i in range(35))

    def create_policy_task(self, agent):
        assigned_check = None
        if self.assigned_check:
            assigned_check = agent.agentchecks.get(parent_check=self.assigned_check.pk)

        task = AutomatedTask.objects.create(
            agent=agent,
            managed_by_policy=True,
            parent_task=self.pk,
            script=self.script,
            assigned_check=assigned_check,
            name=self.name,
            run_time_days=self.run_time_days,
            run_time_minute=self.run_time_minute,
            task_type=self.task_type,
            win_task_name=self.win_task_name,
            timeout=self.timeout,
            enabled=self.enabled,
        )

        autotasks.tasks.create_win_task_schedule.delay(task.pk)
