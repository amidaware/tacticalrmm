from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class ManageAlertsPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET" or r.method == "PATCH":
            return True

        return _has_perm(r, "can_manage_alerts")
