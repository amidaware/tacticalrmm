from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class BrandingPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        # reads are public, the login page needs them
        if r.method in permissions.SAFE_METHODS:
            return True

        return r.user.is_authenticated and _has_perm(r, "can_edit_core_settings")
