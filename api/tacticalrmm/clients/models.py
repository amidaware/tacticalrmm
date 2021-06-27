import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

from agents.models import Agent
from logs.models import BaseAuditModel


class Client(BaseAuditModel):
    name = models.CharField(max_length=255, unique=True)
    block_policy_inheritance = models.BooleanField(default=False)
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
    alert_template = models.ForeignKey(
        "alerts.AlertTemplate",
        related_name="clients",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def save(self, *args, **kw):
        from alerts.tasks import cache_agents_alert_template
        from automation.tasks import generate_agent_checks_task

        # get old client if exists
        old_client = type(self).objects.get(pk=self.pk) if self.pk else None
        super(BaseAuditModel, self).save(*args, **kw)

        # check if polcies have changed and initiate task to reapply policies if so
        if old_client:
            if (
                (old_client.server_policy != self.server_policy)
                or (old_client.workstation_policy != self.workstation_policy)
                or (
                    old_client.block_policy_inheritance != self.block_policy_inheritance
                )
            ):

                generate_agent_checks_task.delay(
                    client=self.pk,
                    create_tasks=True,
                )

            if old_client.alert_template != self.alert_template:
                cache_agents_alert_template.delay()

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    @property
    def agent_count(self) -> int:
        return Agent.objects.filter(site__client=self).count()

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
                "offline_time",
            )
            .filter(site__client=self)
            .prefetch_related("agentchecks", "autotasks")
        )

        data = {"error": False, "warning": False}

        for agent in agents:
            if agent.maintenance_mode:
                break

            if agent.overdue_email_alert or agent.overdue_text_alert:
                if agent.status == "overdue":
                    data["error"] = True
                    break

            if agent.checks["has_failing_checks"]:

                if agent.checks["warning"]:
                    data["warning"] = True

                if agent.checks["failing"]:
                    data["error"] = True
                    break

            if agent.autotasks.exists():  # type: ignore
                for i in agent.autotasks.all():  # type: ignore
                    if i.status == "failing" and i.alert_severity == "error":
                        data["error"] = True
                        break

        return data

    @staticmethod
    def serialize(client):
        # serializes the client and returns json
        from .serializers import ClientSerializer

        return ClientSerializer(client).data


class Site(BaseAuditModel):
    client = models.ForeignKey(Client, related_name="sites", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    block_policy_inheritance = models.BooleanField(default=False)
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
    alert_template = models.ForeignKey(
        "alerts.AlertTemplate",
        related_name="sites",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def save(self, *args, **kw):
        from alerts.tasks import cache_agents_alert_template
        from automation.tasks import generate_agent_checks_task

        # get old client if exists
        old_site = type(self).objects.get(pk=self.pk) if self.pk else None
        super(Site, self).save(*args, **kw)

        # check if polcies have changed and initiate task to reapply policies if so
        if old_site:
            if (
                (old_site.server_policy != self.server_policy)
                or (old_site.workstation_policy != self.workstation_policy)
                or (old_site.block_policy_inheritance != self.block_policy_inheritance)
            ):

                generate_agent_checks_task.delay(site=self.pk, create_tasks=True)

                if old_site.alert_template != self.alert_template:
                    cache_agents_alert_template.delay()

    class Meta:
        ordering = ("name",)
        unique_together = (("client", "name"),)

    def __str__(self):
        return self.name

    @property
    def agent_count(self) -> int:
        return Agent.objects.filter(site=self).count()

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
                "offline_time",
            )
            .filter(site=self)
            .prefetch_related("agentchecks", "autotasks")
        )

        data = {"error": False, "warning": False}

        for agent in agents:
            if agent.maintenance_mode:
                break

            if agent.overdue_email_alert or agent.overdue_text_alert:
                if agent.status == "overdue":
                    data["error"] = True
                    break

            if agent.checks["has_failing_checks"]:
                if agent.checks["warning"]:
                    data["warning"] = True

                if agent.checks["failing"]:
                    data["error"] = True
                    break

            if agent.autotasks.exists():  # type: ignore
                for i in agent.autotasks.all():  # type: ignore
                    if i.status == "failing" and i.alert_severity == "error":
                        data["error"] = True
                        break

        return data

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
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    auth_token = models.ForeignKey(
        "knox.AuthToken", related_name="deploytokens", on_delete=models.CASCADE
    )
    token_key = models.CharField(max_length=255)
    install_flags = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.client} - {self.site} - {self.mon_type}"


class ClientCustomField(models.Model):
    client = models.ForeignKey(
        Client,
        related_name="custom_fields",
        on_delete=models.CASCADE,
    )

    field = models.ForeignKey(
        "core.CustomField",
        related_name="client_fields",
        on_delete=models.CASCADE,
    )

    string_value = models.TextField(null=True, blank=True)
    bool_value = models.BooleanField(blank=True, default=False)
    multiple_value = ArrayField(
        models.TextField(null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )

    def __str__(self):
        return self.field.name

    @property
    def value(self):
        if self.field.type == "multiple":
            return self.multiple_value
        elif self.field.type == "checkbox":
            return self.bool_value
        else:
            return self.string_value


class SiteCustomField(models.Model):
    site = models.ForeignKey(
        Site,
        related_name="custom_fields",
        on_delete=models.CASCADE,
    )

    field = models.ForeignKey(
        "core.CustomField",
        related_name="site_fields",
        on_delete=models.CASCADE,
    )

    string_value = models.TextField(null=True, blank=True)
    bool_value = models.BooleanField(blank=True, default=False)
    multiple_value = ArrayField(
        models.TextField(null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )

    def __str__(self):
        return self.field.name

    @property
    def value(self):
        if self.field.type == "multiple":
            return self.multiple_value
        elif self.field.type == "checkbox":
            return self.bool_value
        else:
            return self.string_value
