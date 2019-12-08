from django.db import models
from agents.models import Agent

PATCH_ACTION_CHOICES = [
    ('inherit', 'Inherit'),
    ('approve', 'Approve'),
    ('ignore', 'Ignore'),
    ('nothing', 'Do Nothing'),
]

class WinUpdate(models.Model):
    agent = models.ForeignKey(Agent, related_name="winupdates", on_delete=models.CASCADE)
    guid = models.CharField(max_length=255, null=True)
    kb = models.CharField(max_length=100, null=True)
    mandatory = models.BooleanField(default=False)
    title = models.TextField(null=True)
    needs_reboot = models.BooleanField(default=False)
    installed = models.BooleanField(default=False)
    downloaded = models.BooleanField(default=False)
    description = models.TextField(null=True)
    severity = models.CharField(max_length=255, null=True, blank=True)
    action = models.CharField(max_length=100, choices=PATCH_ACTION_CHOICES, default="nothing")
    result = models.CharField(max_length=255, default="n/a")

    def __str__(self):
        return f"{self.agent.hostname} {self.kb}"
