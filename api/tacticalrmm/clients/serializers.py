from rest_framework import serializers
from .models import Client, Site

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["client"]

class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = "__all__"

class TreeSerializer(serializers.ModelSerializer):
    client_name = serializers.ReadOnlyField(source="client.client")

    class Meta:
        model = Site
        fields = ('site', 'client_name',)