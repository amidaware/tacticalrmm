from .models import Script
from model_bakery.recipe import Recipe

script = Recipe(
    Script,
    name="Test Script",
    description="Test Desc",
    shell="cmd",
    filename="test.bat",
    script_type="userdefined",
)

builtin_script = script.extend(script_type="builtin")
