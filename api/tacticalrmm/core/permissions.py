from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class CoreSettingsPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_view_core_settings")

        return _has_perm(r, "can_edit_core_settings")


class AITaskPerms(permissions.BasePermission):
    """Scheduled AI tasks are usable by any tech with can_use_ai (not just core
    settings admins). Per-agent access is enforced in the views; the list is
    filtered to the agents the role can see."""

    def has_permission(self, r, view) -> bool:
        from core.models import CoreSettings

        core = CoreSettings.objects.first()
        if not core or not core.ai_module_enabled:
            return False
        return _has_perm(r, "can_use_ai")


class BulkAIPerms(permissions.BasePermission):
    """Bulk AI commands target many agents, so require can_use_ai + can_run_bulk."""

    def has_permission(self, r, view) -> bool:
        from core.models import CoreSettings

        core = CoreSettings.objects.first()
        if not core or not core.ai_module_enabled:
            return False
        return _has_perm(r, "can_use_ai") and _has_perm(r, "can_run_bulk")


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


class SchedulePerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_view_schedules")

        return _has_perm(r, "can_manage_schedules")


class RunServerScriptPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_run_server_scripts")


class WebTerminalPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_use_webterm")
