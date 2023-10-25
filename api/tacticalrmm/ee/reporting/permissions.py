from rest_framework import permissions
from tacticalrmm.permissions import _has_perm


class ReportingPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_view_reports") or _has_perm(
                r, "can_manage_reports"
            )

        return _has_perm(r, "can_manage_reports")


class GenerateReportPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_view_reports") or _has_perm(r, "can_manage_reports")
