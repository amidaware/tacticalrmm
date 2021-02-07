from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import (
    ModelSerializer,
    ReadOnlyField,
    DateTimeField,
)

from clients.serializers import ClientSerializer, SiteSerializer
from automation.serializers import PolicySerializer

from tacticalrmm.utils import get_default_timezone
from .models import Alert, AlertTemplate


class AlertSerializer(ModelSerializer):

    hostname = ReadOnlyField(source="agent.hostname")
    client = ReadOnlyField(source="agent.client.name")
    site = ReadOnlyField(source="agent.site.name")
    alert_time = SerializerMethodField(read_only=True)
    resolved_on = SerializerMethodField(read_only=True)
    snooze_until = SerializerMethodField(read_only=True)

    def get_alert_time(self, instance):
        if instance.alert_time:
            return instance.alert_time.astimezone(get_default_timezone()).timestamp()
        else:
            return None

    def get_resolved_on(self, instance):
        if instance.resolved_on:
            return instance.resolved_on.astimezone(get_default_timezone()).timestamp()
        else:
            return None

    def get_snooze_until(self, instance):
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
