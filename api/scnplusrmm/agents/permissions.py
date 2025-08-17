from rest_framework import permissions

from tacticalrmm.permissions import _has_perm, _has_perm_on_agent


class AgentPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if r.method == "GET":
            if "agent_id" in view.kwargs.keys():
                return _has_perm(r, "can_list_agents") and _has_perm_on_agent(
                    r.user, view.kwargs["agent_id"]
                )
            else:
                return _has_perm(r, "can_list_agents")
        elif r.method == "DELETE":
            return _has_perm(r, "can_uninstall_agents") and _has_perm_on_agent(
                r.user, view.kwargs["agent_id"]
            )
        else:
            if r.path == "/agents/maintenance/bulk/":
                return _has_perm(r, "can_edit_agent")
            else:
                return _has_perm(r, "can_edit_agent") and _has_perm_on_agent(
                    r.user, view.kwargs["agent_id"]
                )


class RecoverAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if "agent_id" not in view.kwargs.keys():
            return _has_perm(r, "can_recover_agents")

        return _has_perm(r, "can_recover_agents") and _has_perm_on_agent(
            r.user, view.kwargs["agent_id"]
        )


class MeshPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_use_mesh") and _has_perm_on_agent(
            r.user, view.kwargs["agent_id"]
        )


class UpdateAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_update_agents")


class ManageProcPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_manage_procs") and _has_perm_on_agent(
            r.user, view.kwargs["agent_id"]
        )


class EvtLogPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_view_eventlogs") and _has_perm_on_agent(
            r.user, view.kwargs["agent_id"]
        )


class SendCMDPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_send_cmd") and _has_perm_on_agent(
            r.user, view.kwargs["agent_id"]
        )


class RebootAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_reboot_agents") and _has_perm_on_agent(
            r.user, view.kwargs["agent_id"]
        )


class InstallAgentPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_install_agents")


class RunScriptPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_run_scripts") and _has_perm_on_agent(
            r.user, view.kwargs["agent_id"]
        )


class AgentNotesPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        # permissions for GET /agents/notes/ endpoint
        if r.method == "GET":
            # permissions for /agents/<agent_id>/notes endpoint
            if "agent_id" in view.kwargs.keys():
                return _has_perm(r, "can_list_notes") and _has_perm_on_agent(
                    r.user, view.kwargs["agent_id"]
                )
            else:
                return _has_perm(r, "can_list_notes")
        else:
            return _has_perm(r, "can_manage_notes")


class RunBulkPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        return _has_perm(r, "can_run_bulk")


class AgentHistoryPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if "agent_id" in view.kwargs.keys():
            return _has_perm(r, "can_list_agent_history") and _has_perm_on_agent(
                r.user, view.kwargs["agent_id"]
            )

        return _has_perm(r, "can_list_agent_history")


class AgentWOLPerms(permissions.BasePermission):
    def has_permission(self, r, view) -> bool:
        if "agent_id" in view.kwargs.keys():
            return _has_perm(r, "can_send_wol") and _has_perm_on_agent(
                r.user, view.kwargs["agent_id"]
            )

        return _has_perm(r, "can_send_wol")
