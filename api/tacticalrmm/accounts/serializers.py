import pyotp
from django.conf import settings
from rest_framework.serializers import (
    ModelSerializer,
    ReadOnlyField,
    SerializerMethodField,
)

from tacticalrmm.util_settings import get_webdomain

from .models import APIKey, Role, User


class UserUISerializer(ModelSerializer):
    class Meta:
        model = User
        fields = [
            "dark_mode",
            "show_community_scripts",
            "agent_dblclick_action",
            "url_action",
            "default_agent_tbl_tab",
            "client_tree_sort",
            "client_tree_splitter",
            "loading_bar_color",
            "dash_info_color",
            "dash_positive_color",
            "dash_negative_color",
            "dash_warning_color",
            "clear_search_when_switching",
            "block_dashboard_login",
            "date_format",
        ]


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "last_login",
            "last_login_ip",
            "role",
            "block_dashboard_login",
            "date_format",
        ]


class TOTPSetupSerializer(ModelSerializer):
    qr_url = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "username",
            "totp_key",
            "qr_url",
        )

    def get_qr_url(self, obj):
        return pyotp.totp.TOTP(obj.totp_key).provisioning_uri(
            obj.username, issuer_name=get_webdomain(settings.CORS_ORIGIN_WHITELIST[0])
        )


class RoleSerializer(ModelSerializer):
    user_count = SerializerMethodField()

    class Meta:
        model = Role
        fields = "__all__"

    def get_user_count(self, obj):
        return obj.users.count()


class RoleAuditSerializer(ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


class APIKeySerializer(ModelSerializer):
    username = ReadOnlyField(source="user.username")

    class Meta:
        model = APIKey
        fields = "__all__"


class APIKeyAuditSerializer(ModelSerializer):
    username = ReadOnlyField(source="user.username")

    class Meta:
        model = APIKey
        fields = [
            "name",
            "username",
            "expiration",
        ]
