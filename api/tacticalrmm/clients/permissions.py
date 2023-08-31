from rest_framework import permissions

from tacticalrmm.permissions import _has_perm, _has_perm_on_client, _has_perm_on_site


class ClientsPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            if "pk" in view.kwargs.keys():
                return _has_perm(r, "can_list_clients") and _has_perm_on_client(
                    r.user, view.kwargs["pk"]
                )
            else:
                return _has_perm(r, "can_list_clients")
        elif r.method in ("PUT", "DELETE"):
            return _has_perm(r, "can_manage_clients") and _has_perm_on_client(
                r.user, view.kwargs["pk"]
            )
        else:
            return _has_perm(r, "can_manage_clients")


class SitesPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            if "pk" in view.kwargs.keys():
                return _has_perm(r, "can_list_sites") and _has_perm_on_site(
                    r.user, view.kwargs["pk"]
                )
            else:
                return _has_perm(r, "can_list_sites")
        elif r.method in ("PUT", "DELETE"):
            return _has_perm(r, "can_manage_sites") and _has_perm_on_site(
                r.user, view.kwargs["pk"]
            )
        else:
            return _has_perm(r, "can_manage_sites")


class DeploymentPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_list_deployments")

        return _has_perm(r, "can_manage_deployments")
