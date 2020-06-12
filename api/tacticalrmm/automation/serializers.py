from rest_framework.serializers import (
    ModelSerializer, 
    SerializerMethodField, 
    StringRelatedField, 
    ReadOnlyField, 
    ValidationError
)

from .models import Policy
from autotasks.models import AutomatedTask
from checks.models import Check
from clients.models import Client
from autotasks.serializers import TaskSerializer
from checks.serializers import CheckSerializer


class PolicySerializer(ModelSerializer):
    class Meta:
        model = Policy
        fields = "__all__"


class PolicyTableSerializer(ModelSerializer):

    clients = StringRelatedField(many=True, read_only=True)
    sites = StringRelatedField(many=True, read_only=True)
    agents = StringRelatedField(many=True, read_only=True)

    clients_count = SerializerMethodField(read_only=True)
    sites_count = SerializerMethodField(read_only=True)
    agents_count = SerializerMethodField(read_only=True)

    class Meta:
        model = Policy
        fields = "__all__"
        depth = 1

    def get_clients_count(self, policy):
        return policy.clients.count()

    def get_sites_count(self, policy):
        return policy.sites.count()

    def get_agents_count(self, policy):
        return policy.agents.count()


class PolicyOverviewSerializer(ModelSerializer):

    class Meta:
        model = Client
        fields = (
            "pk",
            "client",
            "sites",
            "policy"
        )
        depth = 2


class PolicyCheckStatusSerializer(ModelSerializer):

    hostname = ReadOnlyField(source="agent.hostname")

    class Meta:
        model = Check
        fields = "__all__"


class AutoTaskPolicySerializer(ModelSerializer):

    autotasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "autotasks",
        )
        