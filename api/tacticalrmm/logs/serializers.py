from rest_framework import serializers

from .models import PendingAction, AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"

class PendingActionSerializer(serializers.ModelSerializer):

    hostname = serializers.ReadOnlyField(source="agent.hostname")
    salt_id = serializers.ReadOnlyField(source="agent.salt_id")
    client = serializers.ReadOnlyField(source="agent.client")
    site = serializers.ReadOnlyField(source="agent.site")
    due = serializers.ReadOnlyField()
    description = serializers.ReadOnlyField()

    class Meta:
        model = PendingAction
        fields = "__all__"
