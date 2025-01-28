"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import inspect


def get_property_fields(model_class):
    """
    Get all @property fields of a Django model.
    """

    model_name = model_class.__name__
    # make sure model in is reporting models
    if model_name not in [model for model, _ in REPORTING_MODELS]:
        return []

    # excluded properties
    excluded = ["pk", "fields_that_trigger_task_update_on_agent"]

    properties = [
        name
        for name, _ in inspect.getmembers(
            model_class, lambda a: isinstance(a, property)
        )
        if name not in excluded
    ]
    return properties


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
