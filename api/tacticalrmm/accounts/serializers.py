import pyotp
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from .models import User, Role


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
            "clear_search_when_switching",
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
            "role",
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
            obj.username, issuer_name="Tactical RMM"
        )


class RoleSerializer(ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"
