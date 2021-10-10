from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class ManageClientsPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return True

        return _has_perm(r, "can_manage_clients")


class ListClientsPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method != "GET":
            return True

        return _has_perm(r, "can_list_clients")


class ManageSitesPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return True

        return _has_perm(r, "can_manage_sites")


class ListSitesPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method != "GET":
            return True

        return _has_perm(r, "can_list_sites")


class ManageDeploymentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return True

        return _has_perm(r, "can_manage_deployments")


class ListDeploymentsPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method != "GET":
            return True

        return _has_perm(r, "can_list_deployments")
