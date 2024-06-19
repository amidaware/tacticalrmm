from typing import TYPE_CHECKING

from django.shortcuts import get_object_or_404
from rest_framework import permissions

from tacticalrmm.constants import AlertTemplateActionType
from tacticalrmm.permissions import _has_perm, _has_perm_on_agent

if TYPE_CHECKING:
    from accounts.models import User


def _has_perm_on_alert(user: "User", id: int) -> bool:
    from alerts.models import Alert

    role = user.role
    if user.is_superuser or (role and getattr(role, "is_superuser")):
        return True

    # make sure non-superusers with empty roles aren't permitted
    elif not role:
        return False

    alert = get_object_or_404(Alert, id=id)

    if alert.agent:
        agent_id = alert.agent.agent_id
    else:
        return True

    return _has_perm_on_agent(user, agent_id)


class AlertPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method in ("GET", "PATCH"):
            if "pk" in view.kwargs.keys():
                return _has_perm(r, "can_list_alerts") and _has_perm_on_alert(
                    r.user, view.kwargs["pk"]
                )
            else:
                return _has_perm(r, "can_list_alerts")
        else:
            if "pk" in view.kwargs.keys():
                return _has_perm(r, "can_manage_alerts") and _has_perm_on_alert(
                    r.user, view.kwargs["pk"]
                )
            else:
                return _has_perm(r, "can_manage_alerts")


class AlertTemplatePerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            return _has_perm(r, "can_list_alerttemplates")

        if r.method in ("POST", "PUT", "PATCH"):
            # ensure only users with explicit run server script perms can add/modify alert templates
            # while also still requiring the manage alert template perm
            if isinstance(r.data, dict):
                if (
                    r.data.get("action_type") == AlertTemplateActionType.SERVER
                    or r.data.get("resolved_action_type")
                    == AlertTemplateActionType.SERVER
                ):
                    return _has_perm(r, "can_run_server_scripts") and _has_perm(
                        r, "can_manage_alerttemplates"
                    )

        return _has_perm(r, "can_manage_alerttemplates")
