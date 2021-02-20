from rest_framework import serializers

from tacticalrmm.utils import get_default_timezone

from .models import AuditLog, PendingAction


class AuditLogSerializer(serializers.ModelSerializer):

    entry_time = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AuditLog
        fields = "__all__"

    def get_entry_time(self, log):
        timezone = get_default_timezone()
        return log.entry_time.astimezone(timezone).strftime("%m %d %Y %H:%M:%S")


class PendingActionSerializer(serializers.ModelSerializer):

    hostname = serializers.ReadOnlyField(source="agent.hostname")
    salt_id = serializers.ReadOnlyField(source="agent.salt_id")
    client = serializers.ReadOnlyField(source="agent.client.name")
    site = serializers.ReadOnlyField(source="agent.site.name")
    due = serializers.ReadOnlyField()
    description = serializers.ReadOnlyField()

    class Meta:
        model = PendingAction
        fields = "__all__"
