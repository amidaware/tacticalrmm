import importlib
import os
import sys

FUNCTION_REGISTRY = {}

_functions_dir = os.path.dirname(__file__)


def load_functions():
    parent_pkg = __package__
    for filename in sorted(os.listdir(_functions_dir)):
        if filename.startswith("_") or not filename.endswith(".py"):
            continue
        modname = filename[:-3]
        filepath = os.path.join(_functions_dir, filename)
        full_name = f"{parent_pkg}.{modname}"
        spec = importlib.util.spec_from_file_location(full_name, filepath)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = mod
        spec.loader.exec_module(mod)

        handler = getattr(mod, "Handler", None)
        if handler is None:
            continue

        func_name = getattr(handler, "name", None) or modname
        FUNCTION_REGISTRY[func_name.lower()] = handler


load_functions()
