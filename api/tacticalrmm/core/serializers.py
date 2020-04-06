from rest_framework import serializers

from .models import CoreSettings


class CoreSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreSettings
        fields = "__all__"
