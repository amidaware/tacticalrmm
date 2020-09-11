import pytz

from rest_framework import serializers

from .models import Agent
from autotasks.models import AutomatedTask

from winupdate.serializers import WinUpdatePolicySerializer
from automation.serializers import PolicySerializer
from autotasks.serializers import TaskSerializer


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

    def get_last_seen(self, obj):
        agent_tz = pytz.timezone(obj.timezone)
        return obj.last_seen.astimezone(agent_tz).strftime("%b-%d-%Y - %H:%M")

    class Meta:
        model = Agent
        fields = [
            "id",
            "hostname",
            "agent_id",
            "client",
            "site",
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
        ]


class AgentEditSerializer(serializers.ModelSerializer):
    winupdatepolicy = WinUpdatePolicySerializer(many=True, read_only=True)
    all_timezones = serializers.SerializerMethodField()

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
    class Meta:
        model = Agent
        fields = (
            "hostname",
            "pk",
            "client",
            "site",
        )
