import pytz
from rest_framework import serializers

from .models import CodeSignToken, CoreSettings, CustomField, GlobalKVStore, URLAction


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


class CustomFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomField
        fields = "__all__"


class CodeSignTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodeSignToken
        fields = "__all__"


class KeyStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalKVStore
        fields = "__all__"


class URLActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = URLAction
        fields = "__all__"
