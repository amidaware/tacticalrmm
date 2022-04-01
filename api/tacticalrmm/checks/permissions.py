from rest_framework import permissions

from tacticalrmm.permissions import _has_perm, _has_perm_on_agent


class ChecksPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET" or r.method == "PATCH":
            if "agent_id" in view.kwargs.keys():
                return _has_perm(r, "can_list_checks") and _has_perm_on_agent(
                    r.user, view.kwargs["agent_id"]
                )
            else:
                return _has_perm(r, "can_list_checks")
        else:
            return _has_perm(r, "can_manage_checks")


class RunChecksPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_run_checks") and _has_perm_on_agent(
            r.user, view.kwargs["agent_id"]
        )
