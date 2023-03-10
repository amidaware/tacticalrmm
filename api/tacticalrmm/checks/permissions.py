from rest_framework import permissions

from tacticalrmm.permissions import (
    _has_perm,
    _has_perm_on_agent,
    _has_perm_on_client,
    _has_perm_on_site,
)


class ChecksPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method in ("GET", "PATCH"):
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


class BulkRunChecksPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if not _has_perm(r, "can_run_checks"):
            return False

        if view.kwargs["target"] == "client":
            return _has_perm_on_client(user=r.user, client_id=view.kwargs["pk"])

        elif view.kwargs["target"] == "site":
            return _has_perm_on_site(user=r.user, site_id=view.kwargs["pk"])

        return False
