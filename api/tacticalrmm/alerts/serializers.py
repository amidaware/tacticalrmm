from rest_framework.serializers import (
    ModelSerializer,
    ReadOnlyField,
)

from .models import Alert


class AlertSerializer(ModelSerializer):
    
    hostname = ReadOnlyField(source="agent.hostname")
    client = ReadOnlyField(source="agent.client")
    site = ReadOnlyField(source="agent.site")

    class Meta:
        model = Alert
        fields = "__all__"