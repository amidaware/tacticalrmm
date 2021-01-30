from rest_framework.serializers import (
    ModelSerializer,
    ReadOnlyField,
    DateTimeField,
)

from tacticalrmm.utils import get_default_timezone
from .models import Alert, AlertTemplate


class AlertSerializer(ModelSerializer):

    hostname = ReadOnlyField(source="agent.hostname")
    client = ReadOnlyField(source="agent.client.name")
    site = ReadOnlyField(source="agent.site.name")
    alert_time = DateTimeField(
        format="iso-8601", default_timezone=get_default_timezone()
    )
    resolved_on = DateTimeField(
        format="iso-8601", default_timezone=get_default_timezone()
    )
    snooze_until = DateTimeField(
        format="iso-8601", default_timezone=get_default_timezone()
    )

    class Meta:
        model = Alert
        fields = "__all__"


class AlertTemplateSerializer(ModelSerializer):
    agent_settings = ReadOnlyField(source="has_agent_settings")
    check_settings = ReadOnlyField(source="has_check_settings")
    task_settings = ReadOnlyField(source="has_task_settings")

    class Meta:
        model = AlertTemplate
        fields = "__all__"