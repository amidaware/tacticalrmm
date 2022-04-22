from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class AccountsPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_list_accounts")
        else:

            # allow users to reset their own password/2fa see issue #686
            base_path = "/accounts/users/"
            paths = ["reset/", "reset_totp/"]

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
        else:
            return _has_perm(r, "can_manage_roles")


class APIKeyPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_list_api_keys")

        return _has_perm(r, "can_manage_api_keys")
