from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class NetDevicePerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_list_sites")
        elif r.method in ("PUT", "PATCH", "DELETE"):
            return _has_perm(r, "can_manage_sites")
        else:  # POST (create)
            return _has_perm(r, "can_manage_sites")


class NetDeviceConnectPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_use_mesh")
