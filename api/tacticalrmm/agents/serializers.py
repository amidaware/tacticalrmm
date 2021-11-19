import pytz
from rest_framework import serializers
from winupdate.serializers import WinUpdatePolicySerializer

from .models import Agent, AgentCustomField, Note, AgentHistory


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

    def get_all_timezones(self, obj):
        return pytz.all_timezones

    class Meta:
        model = Agent
        exclude = ["id"]


class AgentTableSerializer(serializers.ModelSerializer):
    status = serializers.ReadOnlyField()
    checks = serializers.ReadOnlyField()
    last_seen = serializers.SerializerMethodField()
    client_name = serializers.ReadOnlyField(source="client.name")
    site_name = serializers.ReadOnlyField(source="site.name")
    logged_username = serializers.SerializerMethodField()
    italic = serializers.SerializerMethodField()
    policy = serializers.ReadOnlyField(source="policy.id")
    alert_template = serializers.SerializerMethodField()

    def get_alert_template(self, obj):

        if not obj.alert_template:
            return None
        else:
            return {
                "name": obj.alert_template.name,
                "always_email": obj.alert_template.agent_always_email,
                "always_text": obj.alert_template.agent_always_text,
                "always_alert": obj.alert_template.agent_always_alert,
            }

    def get_last_seen(self, obj) -> str:
        if obj.time_zone is not None:
            agent_tz = pytz.timezone(obj.time_zone)
        else:
            agent_tz = self.context["default_tz"]

        return obj.last_seen.astimezone(agent_tz).strftime("%m %d %Y %H:%M")

    def get_logged_username(self, obj) -> str:
        if obj.logged_in_username == "None" and obj.status == "online":
            return obj.last_logged_in_user
        elif obj.logged_in_username != "None":
            return obj.logged_in_username
        else:
            return "-"

    def get_italic(self, obj) -> bool:
        return obj.logged_in_username == "None" and obj.status == "online"

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
            "has_patches_pending",
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
        ]
        depth = 2


class WinAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = "__all__"


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
    time = serializers.SerializerMethodField(read_only=True)
    script_name = serializers.ReadOnlyField(source="script.name")

    class Meta:
        model = AgentHistory
        fields = "__all__"

    def get_time(self, history):
        tz = self.context["default_tz"]
        return history.time.astimezone(tz).strftime("%m %d %Y %H:%M:%S")


class AgentAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        exclude = ["disks", "services", "wmi_detail"]
