import pytz
from rest_framework import serializers

from clients.serializers import ClientSerializer
from winupdate.serializers import WinUpdatePolicySerializer

from .models import Agent, AgentCustomField, Note


class AgentSerializer(serializers.ModelSerializer):
    # for vue
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
    client_name = serializers.ReadOnlyField(source="client.name")
    site_name = serializers.ReadOnlyField(source="site.name")

    def get_all_timezones(self, obj):
        return pytz.all_timezones

    class Meta:
        model = Agent
        exclude = [
            "last_seen",
        ]


class AgentOverdueActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = [
            "pk",
            "overdue_email_alert",
            "overdue_text_alert",
            "overdue_dashboard_alert",
        ]


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
            "id",
            "alert_template",
            "hostname",
            "agent_id",
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


class AgentEditSerializer(serializers.ModelSerializer):
    winupdatepolicy = WinUpdatePolicySerializer(many=True, read_only=True)
    all_timezones = serializers.SerializerMethodField()
    client = ClientSerializer(read_only=True)
    custom_fields = AgentCustomFieldSerializer(many=True, read_only=True)

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
            "offline_time",
            "overdue_text_alert",
            "overdue_email_alert",
            "all_timezones",
            "winupdatepolicy",
            "policy",
            "custom_fields",
        ]


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
