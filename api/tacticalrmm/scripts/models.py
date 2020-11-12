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


class Script(BaseAuditModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    filename = models.CharField(max_length=255)
    shell = models.CharField(
        max_length=100, choices=SCRIPT_SHELLS, default="powershell"
    )
    script_type = models.CharField(
        max_length=100, choices=SCRIPT_TYPES, default="userdefined"
    )

    def __str__(self):
        return self.filename

    @property
    def filepath(self):
        # for the windows agent when using 'salt-call'
        if self.script_type == "userdefined":
            return f"salt://scripts//userdefined//{self.filename}"
        else:
            return f"salt://scripts//{self.filename}"

    @property
    def file(self):
        if self.script_type == "userdefined":
            return f"/srv/salt/scripts/userdefined/{self.filename}"
        else:
            return f"/srv/salt/scripts/{self.filename}"

    @property
    def code(self):
        try:
            with open(self.file, "r") as f:
                text = f.read()
        except:
            text = "n/a"

        return text

    @classmethod
    def load_community_scripts(cls):
        import json
        import os
        from pathlib import Path
        from django.conf import settings

        # load community uploaded scripts into the database
        # skip ones that already exist, only updating name / desc in case it changes
        # files will be copied by the update script or in docker to /srv/salt/scripts

        # for install script
        try:
            scripts_dir = os.path.join(Path(settings.BASE_DIR).parents[1], "scripts")
        # for docker
        except:
            scripts_dir = os.path.join(Path(settings.BASE_DIR).parents[0], "scripts")

        with open(
            os.path.join(settings.BASE_DIR, "scripts/community_scripts.json")
        ) as f:
            info = json.load(f)

        for script in info:
            if os.path.exists(os.path.join(scripts_dir, script["filename"])):
                s = cls.objects.filter(script_type="builtin").filter(
                    filename=script["filename"]
                )
                if s.exists():
                    i = s.first()
                    i.name = script["name"]
                    i.description = script["description"]
                    i.save(update_fields=["name", "description"])
                else:
                    print(f"Adding new community script: {script['name']}")
                    cls(
                        name=script["name"],
                        description=script["description"],
                        filename=script["filename"],
                        shell=script["shell"],
                        script_type="builtin",
                    ).save()

    @staticmethod
    def serialize(script):
        # serializes the script and returns json
        from .serializers import ScriptSerializer

        return ScriptSerializer(script).data
