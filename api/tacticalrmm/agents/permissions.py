from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class MeshPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_use_mesh")


class UninstallPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_uninstall_agents")


class UpdateAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_update_agents")


class EditAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_edit_agent")


class ManageProcPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_manage_procs")


class EvtLogPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_view_eventlogs")


class SendCMDPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_send_cmd")


class RebootAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_reboot_agents")


class InstallAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_install_agents")


class RunScriptPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_run_scripts")


class ManageNotesPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_manage_notes")


class RunBulkPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_run_bulk")
