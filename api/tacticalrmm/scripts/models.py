import base64
import re
from loguru import logger
from typing import Any, List, Union
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from logs.models import BaseAuditModel

SCRIPT_SHELLS = [
    ("powershell", "Powershell"),
    ("cmd", "Batch (CMD)"),
    ("python", "Python"),
]

SCRIPT_TYPES = [
    ("userdefined", "User Defined"),
    ("builtin", "Built In"),
]

logger.configure(**settings.LOG_CONFIG)


class Script(BaseAuditModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    filename = models.CharField(max_length=255)  # deprecated
    shell = models.CharField(
        max_length=100, choices=SCRIPT_SHELLS, default="powershell"
    )
    script_type = models.CharField(
        max_length=100, choices=SCRIPT_TYPES, default="userdefined"
    )
    args = ArrayField(
        models.TextField(null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    favorite = models.BooleanField(default=False)
    category = models.CharField(max_length=100, null=True, blank=True)
    code_base64 = models.TextField(null=True, blank=True)
    default_timeout = models.PositiveIntegerField(default=90)

    def __str__(self):
        return self.name

    @property
    def code(self):
        if self.code_base64:
            base64_bytes = self.code_base64.encode("ascii", "ignore")
            return base64.b64decode(base64_bytes).decode("ascii", "ignore")
        else:
            return ""

    @classmethod
    def load_community_scripts(cls):
        import json
        import os
        from pathlib import Path

        from django.conf import settings

        # load community uploaded scripts into the database
        # skip ones that already exist, only updating name / desc in case it changes
        # for install script
        if not settings.DOCKER_BUILD:
            scripts_dir = os.path.join(Path(settings.BASE_DIR).parents[1], "scripts")
        # for docker
        else:
            scripts_dir = settings.SCRIPTS_DIR

        with open(
            os.path.join(settings.BASE_DIR, "scripts/community_scripts.json")
        ) as f:
            info = json.load(f)

        for script in info:
            if os.path.exists(os.path.join(scripts_dir, script["filename"])):
                s = cls.objects.filter(script_type="builtin").filter(
                    name=script["name"]
                )

                category = (
                    script["category"] if "category" in script.keys() else "Community"
                )

                default_timeout = (
                    int(script["default_timeout"])
                    if "default_timeout" in script.keys()
                    else 90
                )

                args = script["args"] if "args" in script.keys() else []

                if s.exists():
                    i = s.first()
                    i.name = script["name"]
                    i.description = script["description"]
                    i.category = category
                    i.shell = script["shell"]
                    i.default_timeout = default_timeout
                    i.args = args

                    with open(os.path.join(scripts_dir, script["filename"]), "rb") as f:
                        script_bytes = (
                            f.read().decode("utf-8").encode("ascii", "ignore")
                        )
                        i.code_base64 = base64.b64encode(script_bytes).decode("ascii")

                    i.save(
                        update_fields=[
                            "name",
                            "description",
                            "category",
                            "default_timeout",
                            "code_base64",
                            "shell",
                            "args",
                        ]
                    )
                else:
                    print(f"Adding new community script: {script['name']}")

                    with open(os.path.join(scripts_dir, script["filename"]), "rb") as f:
                        script_bytes = (
                            f.read().decode("utf-8").encode("ascii", "ignore")
                        )
                        code_base64 = base64.b64encode(script_bytes).decode("ascii")

                        cls(
                            code_base64=code_base64,
                            name=script["name"],
                            description=script["description"],
                            filename=script["filename"],
                            shell=script["shell"],
                            script_type="builtin",
                            category=category,
                            default_timeout=default_timeout,
                            args=args,
                        ).save()

    @staticmethod
    def serialize(script):
        # serializes the script and returns json
        from .serializers import ScriptSerializer

        return ScriptSerializer(script).data

    @classmethod
    def parse_script_args(
        cls, agent, shell: str, args: List[str] = list()
    ) -> Union[List[str], None]:
        from core.models import CustomField

        if not list:
            return []

        temp_args = list()

        # pattern to match for injection
        pattern = re.compile(".*\\{\\{(.*)\\}\\}.*")

        for arg in args:
            match = pattern.match(arg)
            if match:
                # only get the match between the () in regex
                string = match.group(1)

                # split by period if exists. First should be model and second should be property
                temp = string.split(".")

                # check for model and property
                if len(temp) != 2:
                    # ignore arg since it is invalid
                    continue

                if temp[0] == "client":
                    model = "client"
                    obj = agent.client
                elif temp[0] == "site":
                    model = "site"
                    obj = agent.site
                elif temp[0] == "agent":
                    model = "agent"
                    obj = agent
                else:
                    # ignore arg since it is invalid
                    continue

                if hasattr(obj, temp[1]):
                    value = getattr(obj, temp[1])

                elif CustomField.objects.filter(model=model, name=temp[1]).exists():

                    field = CustomField.objects.get(model=model, name=temp[1])
                    model_fields = getattr(field, f"{model}_fields")
                    value = None
                    if model_fields.filter(**{model: obj}).exists():
                        value = model_fields.get(**{model: obj}).value

                    if not value and field.default_value:
                        value = field.default_value

                    # check if value exists and if not use defa
                    if value and field.type == "multiple":
                        value = format_shell_array(shell, value)
                    elif value and field.type == "checkbox":
                        value = format_shell_bool(shell, value)

                    if not value:
                        continue

                else:
                    # ignore arg since property is invalid
                    continue

                # replace the value in the arg and push to array
                # log any unhashable type errors
                try:
                    temp_args.append(re.sub("\\{\\{.*\\}\\}", value, arg))  # type: ignore
                except Exception as e:
                    logger.error(e)
                    continue

            else:
                temp_args.append(arg)

        return temp_args


def format_shell_array(shell: str, value: Any) -> str:
    if shell == "cmd":
        return "array args are not supported with batch"
    elif shell == "powershell":
        temp_string = ""
        for item in value:
            temp_string += item + ","
        return temp_string.strip(",")
    else:  # python
        temp_string = ""
        for item in value:
            temp_string += item + ","
        return temp_string.strip(",")


def format_shell_bool(shell: str, value: Any) -> str:
    if shell == "cmd":
        return "1" if value else "0"
    elif shell == "powershell":
        return "$True" if value else "$False"
    else:  # python
        return "True" if value else "False"
