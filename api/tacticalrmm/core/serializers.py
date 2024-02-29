from django.conf import settings
from rest_framework import serializers

from tacticalrmm.constants import ALL_TIMEZONES

from .models import CodeSignToken, CoreSettings, CustomField, GlobalKVStore, URLAction


class CoreSettingsSerializer(serializers.ModelSerializer):
    all_timezones = serializers.SerializerMethodField("all_time_zones")
    mesh_site = serializers.SerializerMethodField()
    mesh_token = serializers.SerializerMethodField()
    mesh_username = serializers.SerializerMethodField()

    def all_time_zones(self, obj):
        return ALL_TIMEZONES

    def get_mesh_site(self, obj):
        if getattr(settings, "HOSTED", False):
            return "n/a"
        return obj.mesh_site

    def get_mesh_token(self, obj):
        if getattr(settings, "HOSTED", False):
            return "n/a"
        return obj.mesh_token

    def get_mesh_username(self, obj):
        if getattr(settings, "HOSTED", False):
            return "n/a"
        return obj.mesh_username

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
