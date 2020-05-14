import random
import string
import datetime as dt


from django.db import models
from django.contrib.postgres.fields import ArrayField
from agents.models import Agent
from clients.models import Site, Client


class Policy(models.Model):
    name = models.CharField(max_length=255, unique=True)
    desc = models.CharField(max_length=255)
    active = models.BooleanField(default=False)
    agents = models.ManyToManyField(Agent, related_name="policies")
    sites = models.ManyToManyField(Site, related_name="policies")
    clients = models.ManyToManyField(Client, related_name="policies")

    def __str__(self):
        return self.name


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
    agent = models.ForeignKey(Agent, related_name="autotasks", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    policy = models.ForeignKey(
        Policy,
        related_name="autotaskpolicy",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    script = models.ForeignKey(
        "checks.Script",
        null=True,
        blank=True,
        related_name="autoscript",
        on_delete=models.CASCADE,
    )
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
    win_task_name = models.CharField(max_length=255, null=True, blank=True)
    timeout = models.PositiveIntegerField(default=120)
    retcode = models.IntegerField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, default="0.0000")
    last_run = models.DateTimeField(null=True, blank=True)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.agent} - {self.name}"

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

    @property
    def assigned_check(self):
        related_checks = (
            "scripttaskfailure",
            "disktaskfailure",
            "pingtaskfailure",
            "cpuloadtaskfailure",
            "memtaskfailure",
            "winsvctaskfailure",
        )

        for i in related_checks:
            obj = getattr(self, i)
            if obj.exists():
                check = obj.get()
                if check.check_type == "script":
                    ret = f"Script Check: {check.script.name}"
                elif check.check_type == "diskspace":
                    ret = f"Disk Space Check: Drive {check.disk}"
                elif check.check_type == "ping":
                    ret = f"Ping Check: {check.name}"
                elif check.check_type == "cpuload":
                    ret = "CPU Load Check"
                elif check.check_type == "memory":
                    ret = "Memory Check"
                elif check.check_type == "winsvc":
                    ret = f"Service Check: {check.svc_display_name}"
                else:
                    ret = "error"

                return ret

    @staticmethod
    def generate_task_name():
        chars = string.ascii_letters
        return "TacticalRMM_" + "".join(random.choice(chars) for i in range(35))

    @staticmethod
    def get_related_check(data):
        from checks.models import (
            DiskCheck,
            ScriptCheck,
            PingCheck,
            CpuLoadCheck,
            MemCheck,
            WinServiceCheck,
        )

        pk = int(data.split("|")[0])
        check_type = data.split("|")[1]
        if check_type == "diskspace":
            return DiskCheck.objects.get(pk=pk)
        elif check_type == "script":
            return ScriptCheck.objects.get(pk=pk)
        elif check_type == "ping":
            return PingCheck.objects.get(pk=pk)
        elif check_type == "cpuload":
            return CpuLoadCheck.objects.get(pk=pk)
        elif check_type == "memory":
            return MemCheck.objects.get(pk=pk)
        elif check_type == "winsvc":
            return WinServiceCheck.objects.get(pk=pk)
