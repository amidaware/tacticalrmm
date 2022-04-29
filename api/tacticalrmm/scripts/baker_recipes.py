from model_bakery.recipe import Recipe
from tacticalrmm.constants import ScriptShell, ScriptType

script = Recipe(
    "scripts.Script",
    name="Test Script",
    description="Test Desc",
    shell=ScriptShell.CMD,
    script_type=ScriptType.USER_DEFINED,
)
