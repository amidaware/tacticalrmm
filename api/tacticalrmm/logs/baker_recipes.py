from itertools import cycle

from model_bakery.recipe import Recipe

from tacticalrmm.constants import AuditActionType, AuditObjType, PAAction, PAStatus

object_types = [
    AuditObjType.USER,
    AuditObjType.SCRIPT,
    AuditObjType.AGENT,
    AuditObjType.POLICY,
    AuditObjType.WINUPDATE,
    AuditObjType.CLIENT,
    AuditObjType.SITE,
    AuditObjType.CHECK,
    AuditObjType.AUTOTASK,
    AuditObjType.CORE,
]

object_actions = [
    AuditActionType.ADD,
    AuditActionType.MODIFY,
    AuditActionType.VIEW,
    AuditActionType.DELETE,
]
agent_actions = [
    AuditActionType.REMOTE_SESSION,
    AuditActionType.EXEC_SCRIPT,
    AuditActionType.EXEC_COMMAND,
]
login_actions = [AuditActionType.FAILED_LOGIN, AuditActionType.LOGIN]

agent_logs = Recipe(
    "logs.AuditLog", action=cycle(agent_actions), object_type=AuditObjType.AGENT
)

object_logs = Recipe(
    "logs.AuditLog", action=cycle(object_actions), object_type=cycle(object_types)
)

login_logs = Recipe(
    "logs.AuditLog", action=cycle(login_actions), object_type=AuditObjType.USER
)

pending_agentupdate_action = Recipe(
    "logs.PendingAction",
    action_type=PAAction.AGENT_UPDATE,
    status=PAStatus.PENDING,
)
