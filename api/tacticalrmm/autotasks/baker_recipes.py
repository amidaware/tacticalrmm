from itertools import cycle

from model_bakery.recipe import Recipe, foreign_key, seq

script = Recipe("scripts.script")

task = Recipe(
    "autotasks.AutomatedTask",
    script=foreign_key(script),
)
