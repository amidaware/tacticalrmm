from rest_framework import permissions
from tacticalrmm.permissions import _is_su


class EditCoreSettingsPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_edit_core_settings


class ServerMaintPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_do_server_maint


class CodeSignPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_code_sign
