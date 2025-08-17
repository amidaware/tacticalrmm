from rest_framework import permissions

from tacticalrmm.permissions import _has_perm, _has_perm_on_agent


class AutoTaskPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            if "agent_id" in view.kwargs.keys():
                return _has_perm(r, "can_list_autotasks") and _has_perm_on_agent(
                    r.user, view.kwargs["agent_id"]
                )
            else:
                return _has_perm(r, "can_list_autotasks")
        else:
            return _has_perm(r, "can_manage_autotasks")


class RunAutoTaskPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_run_autotasks")
