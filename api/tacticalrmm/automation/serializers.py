from rest_framework import serializers

from .models import Policy

class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = "__all__"