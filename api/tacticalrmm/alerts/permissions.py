from rest_framework import permissions

from tacticalrmm.permissions import _has_perm


class AlertPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET" or r.method == "PATCH":
            return _has_perm(r, "can_list_alerts")
        else:
            return _has_perm(r, "can_manage_alerts")

class AlertTemplatePerms(permissions.BasePermission):
    def has_permission(self, r, view):
        if r.method == "GET":
            return _has_perm(r, "can_list_alerttemplates")
        else:
            return _has_perm(r, "can_manage_alerttemplates")