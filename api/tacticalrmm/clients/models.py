from django.db import models
from agents.models import Agent


class Client(models.Model):
    client = models.CharField(max_length=255, unique=True)
    workstation_policy = models.ForeignKey(
        "automation.Policy",
        related_name="workstation_clients",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    server_policy = models.ForeignKey(
        "automation.Policy",
        related_name="server_clients",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_by = models.CharField(max_length=100, null=True, blank=True)
    created_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_by = models.CharField(max_length=100, null=True, blank=True)
    modified_time = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.client

    @property
    def has_failing_checks(self):

        agents = (
            Agent.objects.only("pk", "overdue_email_alert", "overdue_text_alert")
            .filter(client=self.client)
            .prefetch_related("agentchecks")
        )
        for agent in agents:
            if agent.checks["has_failing_checks"]:
                return True

            if agent.overdue_email_alert or agent.overdue_text_alert:
                if agent.status == "overdue":
                    return True

        return False

    @staticmethod
    def serialize(client):
        # serializes the client and returns json
        from .serializers import ClientSerializer
        return ClientSerializer(client).data


class Site(models.Model):
    client = models.ForeignKey(Client, related_name="sites", on_delete=models.CASCADE)
    site = models.CharField(max_length=255)
    workstation_policy = models.ForeignKey(
        "automation.Policy",
        related_name="workstation_sites",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    server_policy = models.ForeignKey(
        "automation.Policy",
        related_name="server_sites",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_by = models.CharField(max_length=100, null=True, blank=True)
    created_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_by = models.CharField(max_length=100, null=True, blank=True)
    modified_time = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.site

    @property
    def has_failing_checks(self):

        agents = (
            Agent.objects.only("pk", "overdue_email_alert", "overdue_text_alert")
            .filter(client=self.client.client)
            .filter(site=self.site)
            .prefetch_related("agentchecks")
        )
        for agent in agents:
            if agent.checks["has_failing_checks"]:
                return True

            if agent.overdue_email_alert or agent.overdue_text_alert:
                if agent.status == "overdue":
                    return True

        return False

    @staticmethod
    def serialize(site):
        # serializes the site and returns json
        from .serializers import SiteSerializer
        return SiteSerializer(site).data

def validate_name(name):
    if "|" in name:
        return False
    else:
        return True
