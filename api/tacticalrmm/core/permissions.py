from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class ViewCoreSettingsPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_view_core_settings")


class EditCoreSettingsPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_edit_core_settings")


class ServerMaintPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_do_server_maint")


class CodeSignPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_code_sign")
