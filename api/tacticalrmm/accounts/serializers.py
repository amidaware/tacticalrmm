import pyotp
from rest_framework.serializers import (
    ModelSerializer,
    SerializerMethodField,
    ReadOnlyField,
)

from .models import User


class UserUISerializer(ModelSerializer):
    class Meta:
        model = User
        fields = [
            "dark_mode",
            "show_community_scripts",
            "agent_dblclick_action",
            "default_agent_tbl_tab",
            "client_tree_sort",
            "client_tree_splitter",
            "loading_bar_color",
        ]


class UserSerializer(ModelSerializer):
    perms = ReadOnlyField()

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
            "is_superuser",
            "can_use_mesh",
            "can_uninstall_agents",
            "can_update_agents",
            "can_edit_agent",
            "can_manage_procs",
            "can_view_eventlogs",
            "can_send_cmd",
            "can_reboot_agents",
            "can_install_agents",
            "can_run_scripts",
            "can_run_bulk",
            "can_manage_notes",
            "can_edit_core_settings",
            "can_do_server_maint",
            "can_code_sign",
            "can_manage_checks",
            "can_run_checks",
            "can_manage_clients",
            "can_manage_sites",
            "can_manage_deployments",
            "can_manage_automation_policies",
            "can_manage_autotasks",
            "can_run_autotasks",
            "can_view_auditlogs",
            "can_manage_pendingactions",
            "can_view_debuglogs",
            "can_manage_scripts",
            "can_manage_alerts",
            "can_manage_winsvcs",
            "can_manage_software",
            "can_manage_winupdates",
            "can_manage_accounts",
            "perms",
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
