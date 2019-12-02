from django.db import models
from agents.models import Agent

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

    def __str__(self):
        return self.agent.hostname
