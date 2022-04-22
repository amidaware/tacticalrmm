from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class CoreSettingsPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_view_core_settings")
        else:
            return _has_perm(r, "can_edit_core_settings")


class URLActionPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_run_urlactions")


class ServerMaintPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_do_server_maint")


class CodeSignPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_code_sign")


class CustomFieldPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_view_customfields")
        else:
            return _has_perm(r, "can_manage_customfields")
