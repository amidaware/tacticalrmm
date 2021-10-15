from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class ClientsPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return _has_perm(r, "can_list_clients")
        
        else:
            return _has_perm(r, "can_manage_clients")


class SitesPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return _has_perm(r, "can_list_sites")
        else:
            return _has_perm(r, "can_manage_sites")


class DeploymentPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return _has_perm(r, "can_list_deployments")
        else:
            return _has_perm(r, "can_manage_deployments")
