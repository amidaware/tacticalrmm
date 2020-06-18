from rest_framework import serializers

from .models import WinUpdate, WinUpdatePolicy
from agents.models import Agent


class WinUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WinUpdate
        fields = "__all__"


class UpdateSerializer(serializers.ModelSerializer):
    winupdates = WinUpdateSerializer(many=True, read_only=True)

    class Meta:
        model = Agent
        fields = (
            "pk",
            "hostname",
            "winupdates",
        )


class WinUpdatePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = WinUpdatePolicy
        fields = "__all__"


class ApprovedUpdateSerializer(serializers.ModelSerializer):
    winupdates = WinUpdateSerializer(read_only=True)
    agentid = serializers.ReadOnlyField(source="agent.pk")
    patch_policy = serializers.SerializerMethodField("get_policies")

    def get_policies(self, obj):
        policy = WinUpdatePolicy.objects.get(agent=obj.agent)
        return WinUpdatePolicySerializer(policy).data

    class Meta:
        model = WinUpdate
        fields = (
            "id",
            "kb",
            "guid",
            "agentid",
            "winupdates",
            "patch_policy",
        )
