import base64
import re
from typing import List, Optional

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from loguru import logger

from logs.models import BaseAuditModel
from tacticalrmm.utils import replace_db_values

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
    guid = name = models.CharField(max_length=64, null=True, blank=True)
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
                s = cls.objects.filter(script_type="builtin", guid=script["guid"])

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

                # check if script was added without a guid
                elif cls.objects.filter(
                    script_type="builtin", name=script["name"]
                ).exists():
                    s = cls.objects.get(script_type="builtin", name=script["name"])

                    if not s.guid:
                        print(f"Updating GUID for: {script['name']}")
                        s.guid = script["guid"]
                        s.name = script["name"]
                        s.description = script["description"]
                        s.category = category
                        s.shell = script["shell"]
                        s.default_timeout = default_timeout
                        s.args = args

                        with open(
                            os.path.join(scripts_dir, script["filename"]), "rb"
                        ) as f:
                            script_bytes = (
                                f.read().decode("utf-8").encode("ascii", "ignore")
                            )
                            s.code_base64 = base64.b64encode(script_bytes).decode(
                                "ascii"
                            )

                        s.save(
                            update_fields=[
                                "guid",
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
                            guid=script["guid"],
                            name=script["name"],
                            description=script["description"],
                            filename=script["filename"],
                            shell=script["shell"],
                            script_type="builtin",
                            category=category,
                            default_timeout=default_timeout,
                            args=args,
                        ).save()

        # delete community scripts that had their name changed
        cls.objects.filter(script_type="builtin", guid=None).delete()

    @staticmethod
    def serialize(script):
        # serializes the script and returns json
        from .serializers import ScriptSerializer

        return ScriptSerializer(script).data

    @classmethod
    def parse_script_args(cls, agent, shell: str, args: List[str] = list()) -> list:

        if not args:
            return []

        temp_args = list()

        # pattern to match for injection
        pattern = re.compile(".*\\{\\{(.*)\\}\\}.*")

        for arg in args:
            match = pattern.match(arg)
            if match:
                # only get the match between the () in regex
                string = match.group(1)
                value = replace_db_values(string=string, agent=agent, shell=shell)

                if value:
                    temp_args.append(re.sub("\\{\\{.*\\}\\}", value, arg))
                else:
                    # pass parameter unaltered
                    temp_args.append(arg)

            else:
                temp_args.append(arg)

        return temp_args
