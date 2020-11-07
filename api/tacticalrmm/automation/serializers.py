from rest_framework.serializers import (
    ModelSerializer,
    SerializerMethodField,
    StringRelatedField,
    ReadOnlyField,
)

from clients.serializers import ClientSerializer, SiteSerializer
from agents.serializers import AgentHostnameSerializer

from .models import Policy
from agents.models import Agent
from autotasks.models import AutomatedTask
from checks.models import Check
from clients.models import Client, Site
from winupdate.serializers import WinUpdatePolicySerializer


class PolicySerializer(ModelSerializer):
    class Meta:
        model = Policy
        fields = "__all__"


class PolicyTableSerializer(ModelSerializer):

    server_clients = ClientSerializer(many=True, read_only=True)
    server_sites = SiteSerializer(many=True, read_only=True)
    workstation_clients = ClientSerializer(many=True, read_only=True)
    workstation_sites = SiteSerializer(many=True, read_only=True)
    agents = AgentHostnameSerializer(many=True, read_only=True)
    default_server_policy = ReadOnlyField(source="is_default_server_policy")
    default_workstation_policy = ReadOnlyField(source="is_default_workstation_policy")
    agents_count = SerializerMethodField(read_only=True)
    winupdatepolicy = WinUpdatePolicySerializer(many=True, read_only=True)

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
        )
        depth = 1


class AutoTasksFieldSerializer(ModelSerializer):
    assigned_check = PolicyCheckSerializer(read_only=True)

    class Meta:
        model = AutomatedTask
        fields = ("id", "enabled", "name", "schedule", "assigned_check")
        depth = 1


class AutoTaskPolicySerializer(ModelSerializer):

    autotasks = AutoTasksFieldSerializer(many=True, read_only=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "autotasks",
        )
        depth = 2


class RelatedClientPolicySerializer(ModelSerializer):
    class Meta:
        model = Client
        fields = ("workstation_policy", "server_policy")
        depth = 1


class RelatedSitePolicySerializer(ModelSerializer):
    class Meta:
        model = Site
        fields = ("workstation_policy", "server_policy")
        depth = 1


class RelatedAgentPolicySerializer(ModelSerializer):
    class Meta:
        model = Agent
        fields = ("policy",)
        depth = 1
