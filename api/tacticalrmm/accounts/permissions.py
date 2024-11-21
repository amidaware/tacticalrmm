from rest_framework import permissions

from tacticalrmm.permissions import _has_perm
from tacticalrmm.utils import get_core_settings


class AccountsPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_list_accounts")

        # allow users to reset their own password/2fa see issue #686
        base_path = "/accounts/users/"
        paths = ("reset/", "reset_totp/")

        if r.path in [base_path + i for i in paths]:
            from accounts.models import User

            try:
                user = User.objects.get(pk=r.data["id"])
            except User.DoesNotExist:
                pass
            else:
                if user == r.user:
                    return True

        return _has_perm(r, "can_manage_accounts")


class RolesPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_list_roles")

        return _has_perm(r, "can_manage_roles")


class APIKeyPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_list_api_keys")

        return _has_perm(r, "can_manage_api_keys")


class LocalUserPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        settings = get_core_settings()
        return not settings.block_local_user_logon


class SelfResetSSOPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return not r.user.is_sso_user
