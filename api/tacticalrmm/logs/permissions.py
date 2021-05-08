from rest_framework import permissions

from tacticalrmm.permissions import _is_su


class AuditLogPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_view_auditlogs


class ManagePendingActionPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "PATCH":
            return True

        return _is_su(r) or r.user.can_manage_pendingactions


class DebugLogPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_view_debuglogs
