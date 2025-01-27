"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

# (Model, app)
REPORTING_MODELS = (
    ("Agent", "agents"),
    ("Note", "agents"),
    ("AgentCustomField", "agents"),
    ("AgentHistory", "agents"),
    ("Alert", "alerts"),
    ("Policy", "automation"),
    ("AutomatedTask", "autotasks"),
    ("TaskResult", "autotasks"),
    ("Check", "checks"),
    ("CheckResult", "checks"),
    ("CheckHistory", "checks"),
    ("Client", "clients"),
    ("ClientCustomField", "clients"),
    ("Site", "clients"),
    ("SiteCustomField", "clients"),
    ("GlobalKVStore", "core"),
    ("AuditLog", "logs"),
    ("DebugLog", "logs"),
    ("PendingAction", "logs"),
    ("ChocoSoftware", "software"),
    ("InstalledSoftware", "software"),
    ("WinUpdate", "winupdate"),
    ("WinUpdatePolicy", "winupdate"),
)

# supported @property fields
AGENT_PROPERTIES = [
    "client",
    "timezone",
    "is_posix",
    "arch",
    "status",
    "checks",
    "pending_actions_count",
    "cpu_model",
    "graphics",
    "local_ips",
    "make_model",
    "physical_disks",
    "serial_number",
]

AGENT_CUSTOM_FIELD_PROPERTIES = [
    "value",
]

ALERT_PROPERTIES = [
    "assigned_agent",
    "site",
    "client",
    "get_result", 
]

POLICY_PROPERTIES = [
    "is_default_server_policy",
    "is_default_workstation_policy"
]

AUTOMATED_TASK_PROPERTIES = [
    "schedule", 
]

CHECK_PROPERTIES = [
    "readable_desc"
]

CHECK_RESULT_PROPERTIES = [
    "history_info"
]

CLIENT_PROPERTIES = [
    "live_agent_count",
]

SITE_PROPERTIES = [
    "live_agent_count"
]

CLIENT_CUSTOM_FIELD_PROPERTIES = [
    "value"
]

SITE_CUSTOM_FIELD_PROPERTIES = [
    "value"
]

# import this
PROPERTIES_MAP = {
    "AGENT": AGENT_PROPERTIES,
    "AGENTCUSTOMFIELD": AGENT_CUSTOM_FIELD_PROPERTIES,
    "ALERT": ALERT_PROPERTIES,
    "POLICY": POLICY_PROPERTIES,
    "AUTOMATEDTASK": AUTOMATED_TASK_PROPERTIES,
    "CHECK": CHECK_PROPERTIES,
    "CHECKRESULT": CHECK_RESULT_PROPERTIES,
    "CLIENT": CLIENT_PROPERTIES,
    "SITE": SITE_PROPERTIES,
    "CLIENTCUSTOMFIELD": CLIENT_CUSTOM_FIELD_PROPERTIES,
    "SITECUSTOMFIELD": SITE_CUSTOM_FIELD_PROPERTIES,
}
