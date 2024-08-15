import uuid
from typing import Dict

from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models

from agents.models import Agent
from logs.models import BaseAuditModel
from tacticalrmm.constants import AGENT_DEFER, AgentMonType, CustomFieldType, GoArch
from tacticalrmm.models import PermissionQuerySet


def _default_failing_checks_data() -> Dict[str, bool]:
    return {"error": False, "warning": False}


class Client(BaseAuditModel):
    objects = PermissionQuerySet.as_manager()

    name = models.CharField(max_length=255, unique=True)
    block_policy_inheritance = models.BooleanField(default=False)
    failing_checks = models.JSONField(default=_default_failing_checks_data)
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

    def save(self, *args, **kwargs):
        from alerts.tasks import cache_agents_alert_template

        # get old client if exists
        old_client = Client.objects.get(pk=self.pk) if self.pk else None
        super().save(old_model=old_client, *args, **kwargs)

        # check if polcies have changed and initiate task to reapply policies if so
        if old_client and (
            old_client.alert_template != self.alert_template
            or old_client.workstation_policy != self.workstation_policy
            or old_client.server_policy != self.server_policy
        ):
            cache_agents_alert_template.delay()

        if old_client and (
            old_client.workstation_policy != self.workstation_policy
            or old_client.server_policy != self.server_policy
        ):
            sites = self.sites.all()
            if old_client.workstation_policy != self.workstation_policy:
                for site in sites:
                    cache.delete_many_pattern(f"site_workstation_*{site.pk}_*")

            if old_client.server_policy != self.server_policy:
                for site in sites:
                    cache.delete_many_pattern(f"site_server_*{site.pk}_*")

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    @property
    def live_agent_count(self) -> int:
        return Agent.objects.defer(*AGENT_DEFER).filter(site__client=self).count()

    @staticmethod
    def serialize(client):
        from .serializers import ClientAuditSerializer

        # serializes the client and returns json
        return ClientAuditSerializer(client).data


class Site(BaseAuditModel):
    objects = PermissionQuerySet.as_manager()

    client = models.ForeignKey(Client, related_name="sites", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    block_policy_inheritance = models.BooleanField(default=False)
    failing_checks = models.JSONField(default=_default_failing_checks_data)
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

    def save(self, *args, **kwargs):
        from alerts.tasks import cache_agents_alert_template

        # get old client if exists
        old_site = Site.objects.get(pk=self.pk) if self.pk else None
        super().save(old_model=old_site, *args, **kwargs)

        # check if polcies have changed and initiate task to reapply policies if so
        if old_site:
            if (
                old_site.alert_template != self.alert_template
                or old_site.workstation_policy != self.workstation_policy
                or old_site.server_policy != self.server_policy
                or old_site.client != self.client
            ):
                cache_agents_alert_template.delay()

            if old_site.workstation_policy != self.workstation_policy:
                cache.delete_many_pattern(f"site_workstation_*{self.pk}_*")

            if old_site.server_policy != self.server_policy:
                cache.delete_many_pattern(f"site_server_*{self.pk}_*")

    class Meta:
        ordering = ("name",)
        unique_together = (("client", "name"),)

    def __str__(self):
        return self.name

    @property
    def live_agent_count(self) -> int:
        return self.agents.defer(*AGENT_DEFER).count()  # type: ignore

    @staticmethod
    def serialize(site):
        from .serializers import SiteAuditSerializer

        # serializes the site and returns json
        return SiteAuditSerializer(site).data


class Deployment(models.Model):
    objects = PermissionQuerySet.as_manager()

    uid = models.UUIDField(primary_key=False, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(
        "clients.Site", related_name="deploysites", on_delete=models.CASCADE
    )
    mon_type = models.CharField(
        max_length=255, choices=AgentMonType.choices, default=AgentMonType.SERVER
    )
    goarch = models.CharField(
        max_length=255, choices=GoArch.choices, default=GoArch.AMD64
    )
    expiry = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    auth_token = models.ForeignKey(
        "knox.AuthToken", related_name="deploytokens", on_delete=models.CASCADE
    )
    token_key = models.CharField(max_length=255)
    install_flags = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.client} - {self.site} - {self.mon_type}"

    @property
    def client(self):
        return self.site.client


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
        if self.field.type == CustomFieldType.MULTIPLE:
            return self.multiple_value
        elif self.field.type == CustomFieldType.CHECKBOX:
            return self.bool_value

        return self.string_value

    def save_to_field(self, value):
        if self.field.type in (
            CustomFieldType.TEXT,
            CustomFieldType.NUMBER,
            CustomFieldType.SINGLE,
            CustomFieldType.DATETIME,
        ):
            self.string_value = value
            self.save()
        elif self.field.type == CustomFieldType.MULTIPLE:
            self.multiple_value = value.split(",")
            self.save()
        elif self.field.type == CustomFieldType.CHECKBOX:
            self.bool_value = bool(value)
            self.save()


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
        if self.field.type == CustomFieldType.MULTIPLE:
            return self.multiple_value
        elif self.field.type == CustomFieldType.CHECKBOX:
            return self.bool_value

        return self.string_value

    def save_to_field(self, value):
        if self.field.type in (
            CustomFieldType.TEXT,
            CustomFieldType.NUMBER,
            CustomFieldType.SINGLE,
            CustomFieldType.DATETIME,
        ):
            self.string_value = value
            self.save()
        elif self.field.type == CustomFieldType.MULTIPLE:
            self.multiple_value = value.split(",")
            self.save()
        elif self.field.type == CustomFieldType.CHECKBOX:
            self.bool_value = bool(value)
            self.save()
