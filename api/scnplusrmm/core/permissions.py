from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class CoreSettingsPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_view_core_settings")

        return _has_perm(r, "can_edit_core_settings")


class GlobalKeyStorePerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_view_global_keystore")

        return _has_perm(r, "can_edit_global_keystore")


class URLActionPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method in {"GET", "PATCH"}:
            return _has_perm(r, "can_run_urlactions")
        elif r.path == "/core/urlaction/run/test/" and r.method == "POST":
            return _has_perm(r, "can_run_urlactions")

        # TODO make a manage url action perm instead?
        return _has_perm(r, "can_edit_core_settings")


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
        elif r.method == "PATCH" and view.__class__.__name__ == "GetAddCustomFields":
            return _has_perm(r, "can_view_customfields")

        return _has_perm(r, "can_manage_customfields")


class RunServerScriptPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_run_server_scripts")


class WebTerminalPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_use_webterm")
