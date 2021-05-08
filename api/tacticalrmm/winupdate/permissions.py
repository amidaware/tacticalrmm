from rest_framework import permissions
from tacticalrmm.permissions import _is_su


class ManageWinUpdatePerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return _is_su(r) or r.user.can_manage_winupdates
