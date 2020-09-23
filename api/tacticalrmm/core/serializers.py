import pytz

from rest_framework import serializers

from .models import CoreSettings


class CoreSettingsSerializer(serializers.ModelSerializer):

    all_timezones = serializers.SerializerMethodField("all_time_zones")

    def all_time_zones(self, obj):
        return pytz.all_timezones

    class Meta:
        model = CoreSettings
        fields = "__all__"


# for audting
class CoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreSettings
        fields = "__all__"
