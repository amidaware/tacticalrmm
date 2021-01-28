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
    class Meta:
        model = AlertTemplate
        fields = "__all__"