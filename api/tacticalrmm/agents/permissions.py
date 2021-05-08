from rest_framework import permissions
from tacticalrmm.permissions import _is_su


class MeshPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_use_mesh


class UninstallPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_uninstall_agents


class UpdateAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_update_agents


class EditAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_edit_agent


class ManageProcPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_manage_procs


class EvtLogPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_view_eventlogs


class SendCMDPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_send_cmd


class RebootAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_reboot_agents


class InstallAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_install_agents


class RunScriptPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_run_scripts


class ManageNotesPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_manage_notes


class RunBulkPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_run_bulk
