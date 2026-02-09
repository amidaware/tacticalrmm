from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class FirewallPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_view_firewall")
        return _has_perm(r, "can_manage_firewall")


class Fail2BanPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_view_firewall")
        return _has_perm(r, "can_manage_firewall")
