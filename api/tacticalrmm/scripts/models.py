import base64
from django.db import models
from logs.models import BaseAuditModel
from django.conf import settings

SCRIPT_SHELLS = [
    ("powershell", "Powershell"),
    ("cmd", "Batch (CMD)"),
    ("python", "Python"),
]

SCRIPT_TYPES = [
    ("userdefined", "User Defined"),
    ("builtin", "Built In"),
]


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
    favorite = models.BooleanField(default=False)
    category = models.CharField(max_length=100, null=True, blank=True)
    code_base64 = models.TextField(null=True, blank=True)

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
                if s.exists():
                    i = s.first()
                    i.name = script["name"]
                    i.description = script["description"]
                    i.category = "Community"
                    i.shell = script["shell"]

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
                            "code_base64",
                            "shell",
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
                            category="Community",
                        ).save()

    @staticmethod
    def serialize(script):
        # serializes the script and returns json
        from .serializers import ScriptSerializer

        return ScriptSerializer(script).data
