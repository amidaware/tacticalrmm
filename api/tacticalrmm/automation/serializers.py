from rest_framework.serializers import (
    ModelSerializer,
    ReadOnlyField,
    SerializerMethodField,
)

from agents.serializers import AgentHostnameSerializer
from autotasks.models import AutomatedTask
from checks.models import Check
from clients.models import Client
from clients.serializers import ClientSerializer, SiteSerializer
from winupdate.serializers import WinUpdatePolicySerializer

from .models import Policy


class PolicySerializer(ModelSerializer):
    class Meta:
        model = Policy
        fields = "__all__"


class PolicyTableSerializer(ModelSerializer):

    default_server_policy = ReadOnlyField(source="is_default_server_policy")
    default_workstation_policy = ReadOnlyField(source="is_default_workstation_policy")
    agents_count = SerializerMethodField(read_only=True)
    winupdatepolicy = WinUpdatePolicySerializer(many=True, read_only=True)
    alert_template = ReadOnlyField(source="alert_template.id")
    excluded_clients = ClientSerializer(many=True)
    excluded_sites = SiteSerializer(many=True)
    excluded_agents = AgentHostnameSerializer(many=True)

    class Meta:
        model = Policy
        fields = "__all__"
        depth = 1

    def get_agents_count(self, policy):
        return policy.related_agents().count()


class PolicyOverviewSerializer(ModelSerializer):
    class Meta:
        model = Client
        fields = ("pk", "name", "sites", "workstation_policy", "server_policy")
        depth = 2


class PolicyCheckStatusSerializer(ModelSerializer):

    hostname = ReadOnlyField(source="agent.hostname")

    class Meta:
        model = Check
        fields = "__all__"


class PolicyTaskStatusSerializer(ModelSerializer):

    hostname = ReadOnlyField(source="agent.hostname")

    class Meta:
        model = AutomatedTask
        fields = "__all__"


class PolicyCheckSerializer(ModelSerializer):
    class Meta:
        model = Check
        fields = (
            "id",
            "check_type",
            "readable_desc",
            "assignedtask",
            "text_alert",
            "email_alert",
            "dashboard_alert",
        )
        depth = 1


class AutoTasksFieldSerializer(ModelSerializer):
    assigned_check = PolicyCheckSerializer(read_only=True)
    script = ReadOnlyField(source="script.id")
    custom_field = ReadOnlyField(source="custom_field.id")

    class Meta:
        model = AutomatedTask
        fields = "__all__"
        depth = 1
