from itertools import cycle
from model_bakery.recipe import Recipe, seq, foreign_key
script = Recipe("scripts.script")

task = Recipe(
    "autotasks.AutomatedTask",
    script=foreign_key(script),
)
