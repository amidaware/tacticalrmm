from rest_framework import serializers

from .models import InstalledSoftware


class InstalledSoftwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstalledSoftware
        fields = "__all__"
