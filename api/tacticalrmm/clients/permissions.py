from rest_framework import permissions
from tacticalrmm.permissions import _is_su


class ManageClientsPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return True

        return _is_su(r) or r.user.can_manage_clients


class ManageSitesPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return True

        return _is_su(r) or r.user.can_manage_sites


class ManageDeploymentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return True

        return _is_su(r) or r.user.can_manage_deployments
