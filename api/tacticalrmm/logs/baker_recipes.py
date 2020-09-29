from logs.models import AuditLog
from model_bakery.recipe import Recipe
from itertools import cycle

object_types = [
    "user",
    "script",
    "agent",
    "policy",
    "winupdatepolicy",
    "client",
    "site",
    "check",
    "automatedtask",
    "coresettings",
]

object_actions = ["add", "modify", "view", "delete"]
agent_actions = ["remote_session", "execute_script", "execute_command"]
login_actions = ["failed_login", "login"]

agent_logs = Recipe(AuditLog, action=cycle(agent_actions), object_type="agent")

object_logs = Recipe(
    AuditLog, action=cycle(object_actions), object_type=cycle(object_types)
)

login_logs = Recipe(AuditLog, action=cycle(login_actions), object_type="user")
