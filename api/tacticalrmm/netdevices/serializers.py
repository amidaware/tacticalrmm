from rest_framework import serializers

from agents.models import Agent

from .models import NetworkDevice


class NetworkDeviceSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    site_name = serializers.ReadOnlyField(source="site.name")
    client_id = serializers.ReadOnlyField(source="site.client.id")
    preferred_agents_info = serializers.SerializerMethodField()

    class Meta:
        model = NetworkDevice
        fields = [
            "id",
            "site",
            "site_name",
            "client_id",
            "client_name",
            "name",
            "protocol",
            "ip_address",
            "port",
            "description",
            "preferred_agents",
            "preferred_agents_info",
            "created_time",
            "modified_time",
        ]

    def get_client_name(self, obj):
        return obj.site.client.name

    def get_preferred_agents_info(self, obj):
        if not obj.preferred_agents:
            return []
        agents = {
            a.agent_id: a
            for a in Agent.objects.filter(agent_id__in=obj.preferred_agents).only(
                "agent_id", "hostname", "last_seen", "overdue_time", "offline_time"
            )
        }
        ret = []
        for agent_id in obj.preferred_agents:
            a = agents.get(agent_id)
            if a:
                ret.append(
                    {
                        "agent_id": a.agent_id,
                        "hostname": a.hostname,
                        "status": a.status,
                    }
                )
        return ret
