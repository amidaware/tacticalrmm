import pytz
from rest_framework import serializers

from agents.models import Agent

from .models import WinUpdate, WinUpdatePolicy


class WinUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WinUpdate
        fields = "__all__"


class WinUpdateSerializerTZAware(serializers.ModelSerializer):
    date_installed = serializers.SerializerMethodField()

    def get_date_installed(self, obj):
        if obj.date_installed is not None:
            if obj.agent.time_zone is not None:
                agent_tz = pytz.timezone(obj.agent.time_zone)
            else:
                agent_tz = self.context["default_tz"]

            return obj.date_installed.astimezone(agent_tz).strftime("%m %d %Y %H:%M")
        return None

    class Meta:
        model = WinUpdate
        fields = "__all__"


class UpdateSerializer(serializers.ModelSerializer):
    winupdates = WinUpdateSerializerTZAware(many=True, read_only=True)

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
