from rest_framework import serializers

from .models import Agent

class AgentSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Agent
        fields = "__all__"

class AgentHostnameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ("hostname",)