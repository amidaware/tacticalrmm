from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class ManageChecksPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return True

        return _has_perm(r, "can_manage_checks")


class RunChecksPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _has_perm(r, "can_run_checks")
