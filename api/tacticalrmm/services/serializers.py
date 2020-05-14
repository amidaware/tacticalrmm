from rest_framework import serializers

from agents.models import Agent


class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = (
            "hostname",
            "pk",
            "services",
        )
