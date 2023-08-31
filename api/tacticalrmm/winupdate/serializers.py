from rest_framework import serializers

from .models import WinUpdate, WinUpdatePolicy


class WinUpdateSerializer(serializers.ModelSerializer):
    date_installed = serializers.SerializerMethodField()

    def get_date_installed(self, obj):
        if obj.date_installed is not None:
            return obj.date_installed.astimezone(self.context["default_tz"]).strftime(
                "%m %d %Y %H:%M"
            )
        return None

    class Meta:
        model = WinUpdate
        fields = "__all__"


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
