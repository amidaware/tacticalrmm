import datetime as dt

from django.db import models
from django.contrib.postgres.fields import ArrayField

from agents.models import Agent

PATCH_ACTION_CHOICES = [
    ("inherit", "Inherit"),
    ("approve", "Approve"),
    ("ignore", "Ignore"),
    ("nothing", "Do Nothing"),
]

AUTO_APPROVAL_CHOICES = [
    ("manual", "Manual"),
    ("approve", "Approve"),
    ("ignore", "Ignore"),
]

RUN_TIME_HOUR_CHOICES = [(i, dt.time(i).strftime("%I %p")) for i in range(24)]

REBOOT_AFTER_INSTALL_CHOICES = [
    ("never", "Never"),
    ("required", "When Required"),
    ("always", "Always"),
]


class WinUpdate(models.Model):
    agent = models.ForeignKey(
        Agent, related_name="winupdates", on_delete=models.CASCADE
    )
    guid = models.CharField(max_length=255, null=True)
    kb = models.CharField(max_length=100, null=True)
    mandatory = models.BooleanField(default=False)
    title = models.TextField(null=True)
    needs_reboot = models.BooleanField(default=False)
    installed = models.BooleanField(default=False)
    downloaded = models.BooleanField(default=False)
    description = models.TextField(null=True)
    severity = models.CharField(max_length=255, null=True, blank=True)
    action = models.CharField(
        max_length=100, choices=PATCH_ACTION_CHOICES, default="nothing"
    )
    result = models.CharField(max_length=255, default="n/a")
    date_installed = models.DateTimeField(null=True)

    def __str__(self):
        return f"{self.agent.hostname} {self.kb}"


class WinUpdatePolicy(models.Model):
    agent = models.ForeignKey(
        "agents.Agent",
        related_name="winupdatepolicy",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    policy = models.ForeignKey(
        "automation.Policy",
        related_name="winupdatepolicy",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    critical = models.CharField(
        max_length=100, choices=AUTO_APPROVAL_CHOICES, default="manual"
    )
    important = models.CharField(
        max_length=100, choices=AUTO_APPROVAL_CHOICES, default="manual"
    )
    moderate = models.CharField(
        max_length=100, choices=AUTO_APPROVAL_CHOICES, default="manual"
    )
    low = models.CharField(
        max_length=100, choices=AUTO_APPROVAL_CHOICES, default="manual"
    )
    other = models.CharField(
        max_length=100, choices=AUTO_APPROVAL_CHOICES, default="manual"
    )

    run_time_hour = models.IntegerField(choices=RUN_TIME_HOUR_CHOICES, default=3)

    # 0 to 6 = Monday to Sunday
    run_time_days = ArrayField(
        models.IntegerField(blank=True), null=True, blank=True, default=list
    )

    reboot_after_install = models.CharField(
        max_length=50, choices=REBOOT_AFTER_INSTALL_CHOICES, default="never"
    )

    reprocess_failed = models.BooleanField(default=False)
    reprocess_failed_times = models.PositiveIntegerField(default=5)
    email_if_fail = models.BooleanField(default=False)

    def __str__(self):
        if self.agent:
            return self.agent.hostname
        else:
            return self.policy.name
