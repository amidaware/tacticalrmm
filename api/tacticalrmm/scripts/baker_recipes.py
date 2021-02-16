from model_bakery.recipe import Recipe

script = Recipe(
    "scripts.Script",
    name="Test Script",
    description="Test Desc",
    shell="cmd",
    script_type="userdefined",
)
