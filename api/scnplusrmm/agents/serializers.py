from rest_framework import serializers

from tacticalrmm.constants import AGENT_STATUS_ONLINE, ALL_TIMEZONES
from winupdate.serializers import WinUpdatePolicySerializer

from .models import Agent, AgentCustomField, AgentHistory, Note


class AgentCustomFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentCustomField
        fields = (
            "id",
            "field",
            "agent",
            "value",
            "string_value",
            "bool_value",
            "multiple_value",
        )
        extra_kwargs = {
            "string_value": {"write_only": True},
            "bool_value": {"write_only": True},
            "multiple_value": {"write_only": True},
        }


class AgentSerializer(serializers.ModelSerializer):
    winupdatepolicy = WinUpdatePolicySerializer(many=True, read_only=True)
    status = serializers.ReadOnlyField()
    cpu_model = serializers.ReadOnlyField()
    local_ips = serializers.ReadOnlyField()
    make_model = serializers.ReadOnlyField()
    physical_disks = serializers.ReadOnlyField()
    graphics = serializers.ReadOnlyField()
    checks = serializers.ReadOnlyField()
    timezone = serializers.ReadOnlyField()
    all_timezones = serializers.SerializerMethodField()
    client = serializers.ReadOnlyField(source="client.name")
    site_name = serializers.ReadOnlyField(source="site.name")
    custom_fields = AgentCustomFieldSerializer(many=True, read_only=True)
    patches_last_installed = serializers.ReadOnlyField()
    last_seen = serializers.ReadOnlyField()
    applied_policies = serializers.SerializerMethodField()
    effective_patch_policy = serializers.SerializerMethodField()
    alert_template = serializers.SerializerMethodField()

    def get_alert_template(self, obj):
        from alerts.serializers import AlertTemplateSerializer

        return (
            AlertTemplateSerializer(obj.alert_template).data
            if obj.alert_template
            else None
        )

    def get_effective_patch_policy(self, obj):
        return WinUpdatePolicySerializer(obj.get_patch_policy()).data

    def get_applied_policies(self, obj):
        from automation.serializers import PolicySerializer

        policies = obj.get_agent_policies()

        # need to serialize model objects manually
        for key, policy in policies.items():
            if policy:
                policies[key] = PolicySerializer(policy).data

        return policies

    def get_all_timezones(self, obj):
        return ALL_TIMEZONES

    class Meta:
        model = Agent
        exclude = ["id"]


class AgentTableSerializer(serializers.ModelSerializer):
    status = serializers.ReadOnlyField()
    checks = serializers.ReadOnlyField()
    client_name = serializers.ReadOnlyField(source="client.name")
    site_name = serializers.ReadOnlyField(source="site.name")
    logged_username = serializers.SerializerMethodField()
    italic = serializers.SerializerMethodField()
    policy = serializers.ReadOnlyField(source="policy.id")
    alert_template = serializers.SerializerMethodField()
    last_seen = serializers.ReadOnlyField()
    pending_actions_count = serializers.ReadOnlyField()
    has_patches_pending = serializers.ReadOnlyField()
    cpu_model = serializers.ReadOnlyField()
    graphics = serializers.ReadOnlyField()
    local_ips = serializers.ReadOnlyField()
    make_model = serializers.ReadOnlyField()
    physical_disks = serializers.ReadOnlyField()
    serial_number = serializers.ReadOnlyField()
    custom_fields = AgentCustomFieldSerializer(many=True, read_only=True)

    def get_alert_template(self, obj):
        if not obj.alert_template:
            return None

        return {
            "name": obj.alert_template.name,
            "always_email": obj.alert_template.agent_always_email,
            "always_text": obj.alert_template.agent_always_text,
            "always_alert": obj.alert_template.agent_always_alert,
        }

    def get_logged_username(self, obj) -> str:
        if obj.logged_in_username == "None" and obj.status == AGENT_STATUS_ONLINE:
            return obj.last_logged_in_user
        elif obj.logged_in_username != "None":
            return obj.logged_in_username

        return "-"

    def get_italic(self, obj) -> bool:
        return obj.logged_in_username == "None" and obj.status == AGENT_STATUS_ONLINE

    class Meta:
        model = Agent
        fields = [
            "agent_id",
            "alert_template",
            "hostname",
            "site_name",
            "client_name",
            "monitoring_type",
            "description",
            "needs_reboot",
            "pending_actions_count",
            "status",
            "overdue_text_alert",
            "overdue_email_alert",
            "overdue_dashboard_alert",
            "last_seen",
            "boot_time",
            "checks",
            "maintenance_mode",
            "logged_username",
            "italic",
            "policy",
            "block_policy_inheritance",
            "plat",
            "goarch",
            "has_patches_pending",
            "version",
            "operating_system",
            "public_ip",
            "cpu_model",
            "graphics",
            "local_ips",
            "make_model",
            "physical_disks",
            "custom_fields",
            "serial_number",
        ]
        depth = 2


class AgentHostnameSerializer(serializers.ModelSerializer):
    client = serializers.ReadOnlyField(source="client.name")
    site = serializers.ReadOnlyField(source="site.name")

    class Meta:
        model = Agent
        fields = (
            "id",
            "hostname",
            "agent_id",
            "client",
            "site",
        )


class AgentNoteSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")
    agent_id = serializers.ReadOnlyField(source="agent.agent_id")

    class Meta:
        model = Note
        fields = ("pk", "entry_time", "agent", "user", "note", "username", "agent_id")
        extra_kwargs = {"agent": {"write_only": True}, "user": {"write_only": True}}


class AgentHistorySerializer(serializers.ModelSerializer):
    script_name = serializers.ReadOnlyField(source="script.name")

    class Meta:
        model = AgentHistory
        fields = "__all__"


class AgentAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        exclude = ["disks", "services", "wmi_detail"]
