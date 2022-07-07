from model_bakery.recipe import Recipe

from tacticalrmm.constants import AgentPlat, ScriptShell, ScriptType
from tacticalrmm.demo_data import (
    check_storage_pool_health_ps1,
    clear_print_spool_bat,
    redhat_insights,
    show_temp_dir_py,
)

script = Recipe(
    "scripts.Script",
    name="Test Script",
    description="Test Desc",
    shell=ScriptShell.CMD,
    script_type=ScriptType.USER_DEFINED,
)

batch_script = Recipe(
    "scripts.Script",
    name="Test Batch Script",
    description="Test Batch Desc",
    shell=ScriptShell.CMD,
    script_type=ScriptType.USER_DEFINED,
    script_body=clear_print_spool_bat,
    args=["one", "two"],
)

ps_script = Recipe(
    "scripts.Script",
    name="Test Powershell Script",
    description="Test Powershell Desc",
    shell=ScriptShell.POWERSHELL,
    script_type=ScriptType.USER_DEFINED,
    script_body=check_storage_pool_health_ps1,
    args=["one"],
    supported_platforms=[AgentPlat.WINDOWS],
)

py_script = Recipe(
    "scripts.Script",
    name="Test Python Script",
    description="Test Python Desc",
    shell=ScriptShell.PYTHON,
    script_body=show_temp_dir_py,
    script_type=ScriptType.USER_DEFINED,
    supported_platforms=[AgentPlat.WINDOWS, AgentPlat.LINUX],
    category="py stuff",
)

bash_script = Recipe(
    "scripts.Script",
    name="Test Bash Script",
    description="Test Bash Desc",
    shell=ScriptShell.SHELL,
    script_body=redhat_insights,
    script_type=ScriptType.USER_DEFINED,
    args=["one"],
    supported_platforms=[AgentPlat.LINUX],
    category="RHSA",
)
