from rest_framework import permissions
from tacticalrmm.permissions import _is_su


class ManageAlertsPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET" or r.method == "PATCH":
            return True

        return _is_su(r) or r.user.can_manage_alerts
