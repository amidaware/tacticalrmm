import uuid

from django.db import models

from agents.models import Agent
from logs.models import BaseAuditModel


class Client(BaseAuditModel):
    name = models.CharField(max_length=255, unique=True)
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

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    @property
    def has_maintenanace_mode_agents(self):
        return (
            Agent.objects.filter(site__client=self, maintenance_mode=True).count() > 0
        )

    @property
    def has_failing_checks(self):

        agents = (
            Agent.objects.only(
                "pk",
                "overdue_email_alert",
                "overdue_text_alert",
                "last_seen",
                "overdue_time",
            )
            .filter(site__client=self)
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


class Site(BaseAuditModel):
    client = models.ForeignKey(Client, related_name="sites", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
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

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    @property
    def has_maintenanace_mode_agents(self):
        return Agent.objects.filter(site=self, maintenance_mode=True).count() > 0

    @property
    def has_failing_checks(self):

        agents = (
            Agent.objects.only(
                "pk",
                "overdue_email_alert",
                "overdue_text_alert",
                "last_seen",
                "overdue_time",
            )
            .filter(site=self)
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


MON_TYPE_CHOICES = [
    ("server", "Server"),
    ("workstation", "Workstation"),
]

ARCH_CHOICES = [
    ("64", "64 bit"),
    ("32", "32 bit"),
]


class Deployment(models.Model):
    uid = models.UUIDField(primary_key=False, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        "clients.Client", related_name="deployclients", on_delete=models.CASCADE
    )
    site = models.ForeignKey(
        "clients.Site", related_name="deploysites", on_delete=models.CASCADE
    )
    mon_type = models.CharField(
        max_length=255, choices=MON_TYPE_CHOICES, default="server"
    )
    arch = models.CharField(max_length=255, choices=ARCH_CHOICES, default="64")
    expiry = models.DateTimeField(null=True, blank=True)
    auth_token = models.ForeignKey(
        "knox.AuthToken", related_name="deploytokens", on_delete=models.CASCADE
    )
    token_key = models.CharField(max_length=255)
    install_flags = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.client} - {self.site} - {self.mon_type}"
