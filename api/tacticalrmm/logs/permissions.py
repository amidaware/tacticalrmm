from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class AuditLogPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_view_auditlogs")


class ManagePendingActionPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "PATCH":
            return True

        return _has_perm(r, "can_manage_pendingactions")


class DebugLogPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_view_debuglogs")
