import pytz

from rest_framework import serializers
from rest_framework.fields import ReadOnlyField

from .models import Agent, Note

from winupdate.serializers import WinUpdatePolicySerializer
from clients.serializers import ClientSerializer


class AgentSerializer(serializers.ModelSerializer):
    # for vue
    patches_pending = serializers.ReadOnlyField(source="has_patches_pending")
    winupdatepolicy = WinUpdatePolicySerializer(many=True, read_only=True)
    status = serializers.ReadOnlyField()
    cpu_model = serializers.ReadOnlyField()
    local_ips = serializers.ReadOnlyField()
    make_model = serializers.ReadOnlyField()
    physical_disks = serializers.ReadOnlyField()
    checks = serializers.ReadOnlyField()
    timezone = serializers.ReadOnlyField()
    all_timezones = serializers.SerializerMethodField()
    client_name = serializers.ReadOnlyField(source="client.name")
    site_name = serializers.ReadOnlyField(source="site.name")

    def get_all_timezones(self, obj):
        return pytz.all_timezones

    class Meta:
        model = Agent
        exclude = [
            "last_seen",
        ]


class AgentTableSerializer(serializers.ModelSerializer):
    patches_pending = serializers.ReadOnlyField(source="has_patches_pending")
    status = serializers.ReadOnlyField()
    checks = serializers.ReadOnlyField()
    last_seen = serializers.SerializerMethodField()
    client_name = serializers.ReadOnlyField(source="client.name")
    site_name = serializers.ReadOnlyField(source="site.name")

    def get_last_seen(self, obj):
        if obj.time_zone is not None:
            agent_tz = pytz.timezone(obj.time_zone)
        else:
            agent_tz = self.context["default_tz"]

        return obj.last_seen.astimezone(agent_tz).strftime("%m %d %Y %H:%M:%S")

    class Meta:
        model = Agent
        fields = [
            "id",
            "hostname",
            "agent_id",
            "site_name",
            "client_name",
            "monitoring_type",
            "description",
            "needs_reboot",
            "patches_pending",
            "status",
            "overdue_text_alert",
            "overdue_email_alert",
            "last_seen",
            "boot_time",
            "checks",
            "logged_in_username",
            "last_logged_in_user",
            "maintenance_mode",
        ]
        depth = 2


class AgentEditSerializer(serializers.ModelSerializer):
    winupdatepolicy = WinUpdatePolicySerializer(many=True, read_only=True)
    all_timezones = serializers.SerializerMethodField()
    client = ClientSerializer(read_only=True)

    def get_all_timezones(self, obj):
        return pytz.all_timezones

    class Meta:
        model = Agent
        fields = [
            "id",
            "hostname",
            "client",
            "site",
            "monitoring_type",
            "description",
            "time_zone",
            "timezone",
            "check_interval",
            "overdue_time",
            "overdue_text_alert",
            "overdue_email_alert",
            "all_timezones",
            "winupdatepolicy",
        ]


class WinAgentSerializer(serializers.ModelSerializer):
    # for the windows agent
    patches_pending = serializers.ReadOnlyField(source="has_patches_pending")
    winupdatepolicy = WinUpdatePolicySerializer(many=True, read_only=True)
    status = serializers.ReadOnlyField()

    class Meta:
        model = Agent
        fields = "__all__"


class AgentHostnameSerializer(serializers.ModelSerializer):
    client = serializers.ReadOnlyField(source="client.name")
    site = serializers.ReadOnlyField(source="site.name")

    class Meta:
        model = Agent
        fields = (
            "hostname",
            "pk",
            "client",
            "site",
        )


class NoteSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Note
        fields = "__all__"


class NotesSerializer(serializers.ModelSerializer):
    notes = NoteSerializer(many=True, read_only=True)

    class Meta:
        model = Agent
        fields = ["hostname", "pk", "notes"]
