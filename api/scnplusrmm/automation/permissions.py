from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class AutomationPolicyPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_list_automation_policies")

        return _has_perm(r, "can_manage_automation_policies")
