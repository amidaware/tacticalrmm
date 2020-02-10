from rest_framework import serializers

from .models import ChocoSoftware, InstalledSoftware


class ChocoSoftwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChocoSoftware
        fields = "__all__"


class InstalledSoftwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstalledSoftware
        fields = "__all__"
