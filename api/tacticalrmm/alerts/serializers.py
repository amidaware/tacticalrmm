from rest_framework.serializers import (
    ModelSerializer,
    ReadOnlyField,
    DateTimeField,
)

from .models import Alert


class AlertSerializer(ModelSerializer):

    hostname = ReadOnlyField(source="agent.hostname")
    client = ReadOnlyField(source="agent.client")
    site = ReadOnlyField(source="agent.site")
    alert_time = DateTimeField(format="iso-8601")

    class Meta:
        model = Alert
        fields = "__all__"