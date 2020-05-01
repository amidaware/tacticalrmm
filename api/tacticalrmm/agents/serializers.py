from rest_framework import serializers

from .models import Agent
from automation.models import AutomatedTask

from winupdate.serializers import WinUpdatePolicySerializer
from automation.serializers import TaskSerializer, PolicySerializer


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

    class Meta:
        model = Agent
        exclude = ["wmi_detail", "services"]


class AgentTableSerializer(serializers.ModelSerializer):
    patches_pending = serializers.ReadOnlyField(source="has_patches_pending")
    status = serializers.ReadOnlyField()

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
