"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

# (Model, app)
REPORTING_MODELS = (
    ("Agent", "agents"),
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
