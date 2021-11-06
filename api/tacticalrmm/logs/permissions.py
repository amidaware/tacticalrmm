from rest_framework import permissions

from tacticalrmm.permissions import _has_perm, _has_perm_on_agent


class AuditLogPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_view_auditlogs")


class PendingActionPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            if "agent_id" in view.kwargs.keys():
                return _has_perm(r, "can_list_pendingactions") and _has_perm_on_agent(
                    r.user, view.kwargs["agent_id"]
                )
            else:
                return _has_perm(r, "can_list_pendingactions")
        else:
            return _has_perm(r, "can_manage_pendingactions")


class DebugLogPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_view_debuglogs")
