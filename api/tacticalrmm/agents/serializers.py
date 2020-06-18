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
    salt_id = serializers.ReadOnlyField()
    winupdatepolicy = WinUpdatePolicySerializer(many=True, read_only=True)
    status = serializers.ReadOnlyField()
    cpu_model = serializers.ReadOnlyField()
    local_ips = serializers.ReadOnlyField()
    make_model = serializers.ReadOnlyField()
    physical_disks = serializers.ReadOnlyField()
    checks = serializers.ReadOnlyField()
    timezone = serializers.ReadOnlyField()
    all_timezones = serializers.SerializerMethodField("all_time_zones")

    def all_time_zones(self, obj):
        return pytz.all_timezones

    class Meta:
        model = Agent
        exclude = [
            "wmi_detail",
            "last_seen",
        ]


class AgentTableSerializer(serializers.ModelSerializer):
    patches_pending = serializers.ReadOnlyField(source="has_patches_pending")
    status = serializers.ReadOnlyField()
    checks = serializers.ReadOnlyField()
    timezone = serializers.ReadOnlyField()

    class Meta:
        model = Agent
        fields = [
            "id",
            "hostname",
            "plat",
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
            "timezone",
        ]


class WinAgentSerializer(serializers.ModelSerializer):
    # for the windows agent
    patches_pending = serializers.ReadOnlyField(source="has_patches_pending")
    salt_id = serializers.ReadOnlyField()
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
