from rest_framework import serializers

from agents.models import Agent
from clients.models import Client, Site


class ListAgentSerializer(serializers.ModelSerializer[Agent]):
    class Meta:
        model = Agent
        fields = "__all__"


class DetailAgentSerializer(serializers.ModelSerializer[Agent]):
    status = serializers.ReadOnlyField()

    class Meta:
        model = Agent
        fields = (
            "version",
            "operating_system",
            "plat",
            "goarch",
            "hostname",
            "agent_id",
            "last_seen",
            "services",
            "public_ip",
            "total_ram",
            "disks",
            "boot_time",
            "logged_in_username",
            "last_logged_in_user",
            "monitoring_type",
            "description",
            "mesh_node_id",
            "overdue_email_alert",
            "overdue_text_alert",
            "overdue_dashboard_alert",
            "offline_time",
            "overdue_time",
            "check_interval",
            "needs_reboot",
            "choco_installed",
            "wmi_detail",
            "patches_last_installed",
            "time_zone",
            "maintenance_mode",
            "block_policy_inheritance",
            "alert_template",
            "site",
            "policy",
            "status",
            "checks",
            "pending_actions_count",
            "cpu_model",
            "graphics",
            "local_ips",
            "make_model",
            "physical_disks",
            "serial_number",
        )


class ClientSerializer(serializers.ModelSerializer[Client]):
    class Meta:
        model = Client
        fields = "__all__"


class SiteSerializer(serializers.ModelSerializer[Site]):
    class Meta:
        model = Site
        fields = "__all__"
