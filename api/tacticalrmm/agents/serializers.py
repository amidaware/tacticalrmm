from rest_framework import serializers

from .models import Agent

from winupdate.serializers import WinUpdatePolicySerializer


class AgentSerializer(serializers.ModelSerializer):

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
