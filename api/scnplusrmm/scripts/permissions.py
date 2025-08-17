from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class ScriptsPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_list_scripts")

        return _has_perm(r, "can_manage_scripts")
