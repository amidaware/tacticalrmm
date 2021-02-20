from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer, ReadOnlyField

from automation.serializers import PolicySerializer
from clients.serializers import ClientSerializer, SiteSerializer
from tacticalrmm.utils import get_default_timezone

from .models import Alert, AlertTemplate


class AlertSerializer(ModelSerializer):

    hostname = SerializerMethodField(read_only=True)
    client = SerializerMethodField(read_only=True)
    site = SerializerMethodField(read_only=True)
    alert_time = SerializerMethodField(read_only=True)
    resolve_on = SerializerMethodField(read_only=True)
    snoozed_until = SerializerMethodField(read_only=True)

    def get_hostname(self, instance):
        if instance.alert_type == "availability":
            return instance.agent.hostname if instance.agent else ""
        elif instance.alert_type == "check":
            return (
                instance.assigned_check.agent.hostname
                if instance.assigned_check
                else ""
            )
        elif instance.alert_type == "task":
            return (
                instance.assigned_task.agent.hostname if instance.assigned_task else ""
            )
        else:
            return ""

    def get_client(self, instance):
        if instance.alert_type == "availability":
            return instance.agent.client.name if instance.agent else ""
        elif instance.alert_type == "check":
            return (
                instance.assigned_check.agent.client.name
                if instance.assigned_check
                else ""
            )
        elif instance.alert_type == "task":
            return (
                instance.assigned_task.agent.client.name
                if instance.assigned_task
                else ""
            )
        else:
            return ""

    def get_site(self, instance):
        if instance.alert_type == "availability":
            return instance.agent.site.name if instance.agent else ""
        elif instance.alert_type == "check":
            return (
                instance.assigned_check.agent.site.name
                if instance.assigned_check
                else ""
            )
        elif instance.alert_type == "task":
            return (
                instance.assigned_task.agent.site.name if instance.assigned_task else ""
            )
        else:
            return ""

    def get_alert_time(self, instance):
        if instance.alert_time:
            return instance.alert_time.astimezone(get_default_timezone()).timestamp()
        else:
            return None

    def get_resolve_on(self, instance):
        if instance.resolved_on:
            return instance.resolved_on.astimezone(get_default_timezone()).timestamp()
        else:
            return None

    def get_snoozed_until(self, instance):
        if instance.snooze_until:
            return instance.snooze_until.astimezone(get_default_timezone()).timestamp()
        return None

    class Meta:
        model = Alert
        fields = "__all__"


class AlertTemplateSerializer(ModelSerializer):
    agent_settings = ReadOnlyField(source="has_agent_settings")
    check_settings = ReadOnlyField(source="has_check_settings")
    task_settings = ReadOnlyField(source="has_task_settings")
    core_settings = ReadOnlyField(source="has_core_settings")
    default_template = ReadOnlyField(source="is_default_template")
    action_name = ReadOnlyField(source="action.name")
    resolved_action_name = ReadOnlyField(source="resolved_action.name")
    applied_count = SerializerMethodField()

    class Meta:
        model = AlertTemplate
        fields = "__all__"

    def get_applied_count(self, instance):
        count = 0
        count += instance.policies.count()
        count += instance.clients.count()
        count += instance.sites.count()
        return count


class AlertTemplateRelationSerializer(ModelSerializer):
    policies = PolicySerializer(read_only=True, many=True)
    clients = ClientSerializer(read_only=True, many=True)
    sites = SiteSerializer(read_only=True, many=True)

    class Meta:
        model = AlertTemplate
        fields = "__all__"
