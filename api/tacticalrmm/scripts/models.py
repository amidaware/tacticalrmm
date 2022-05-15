import hashlib
import hmac
import re
from typing import List

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.fields import CharField, TextField

from logs.models import BaseAuditModel
from tacticalrmm.constants import ScriptShell, ScriptType
from tacticalrmm.utils import replace_db_values


class Script(BaseAuditModel):
    guid = models.CharField(max_length=64, null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True, default="")
    filename = models.CharField(max_length=255, null=True, blank=True)
    shell = models.CharField(
        max_length=100, choices=ScriptShell.choices, default=ScriptShell.POWERSHELL
    )
    script_type = models.CharField(
        max_length=100, choices=ScriptType.choices, default=ScriptType.USER_DEFINED
    )
    args = ArrayField(
        models.TextField(null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    syntax = TextField(null=True, blank=True)
    favorite = models.BooleanField(default=False)
    category = models.CharField(max_length=100, null=True, blank=True)
    script_body = models.TextField(blank=True, default="")
    script_hash = models.CharField(max_length=100, null=True, blank=True)
    code_base64 = models.TextField(blank=True, default="")  # deprecated
    default_timeout = models.PositiveIntegerField(default=90)
    hidden = models.BooleanField(default=False)
    supported_platforms = ArrayField(
        models.CharField(max_length=20), null=True, blank=True, default=list
    )

    def __str__(self):
        return self.name

    @property
    def code_no_snippets(self):
        return self.script_body if self.script_body else ""

    @property
    def code(self):
        return self.replace_with_snippets(self.code_no_snippets)

    @classmethod
    def replace_with_snippets(cls, code):
        # check if snippet has been added to script body
        matches = re.finditer(r"{{(.*)}}", code)
        if matches:
            replaced_code = code
            for snippet in matches:
                snippet_name = snippet.group(1).strip()
                if ScriptSnippet.objects.filter(name=snippet_name).exists():
                    value = ScriptSnippet.objects.get(name=snippet_name).code
                else:
                    value = ""

                replaced_code = re.sub(snippet.group(), value, replaced_code)

            return replaced_code
        else:
            return code

    def hash_script_body(self):
        from django.conf import settings

        msg = self.code.encode(errors="ignore")
        return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()

    @classmethod
    def load_community_scripts(cls):
        import json
        import os

        from django.conf import settings

        # load community uploaded scripts into the database
        # skip ones that already exist, only updating name / desc in case it changes
        # for install script
        scripts_dir = os.path.join(settings.SCRIPTS_DIR, "scripts")

        with open(os.path.join(settings.SCRIPTS_DIR, "community_scripts.json")) as f:
            info = json.load(f)

        # used to remove scripts from DB that are removed from the json file and file system
        community_scripts_processed = []  # list of script guids

        for script in info:
            if os.path.exists(os.path.join(scripts_dir, script["filename"])):
                s = cls.objects.filter(
                    script_type=ScriptType.BUILT_IN, guid=script["guid"]
                )

                category = (
                    script["category"] if "category" in script.keys() else "Community"
                )

                default_timeout = (
                    int(script["default_timeout"])
                    if "default_timeout" in script.keys()
                    else 90
                )

                args = script["args"] if "args" in script.keys() else list()

                syntax = script["syntax"] if "syntax" in script.keys() else ""

                supported_platforms = (
                    script["supported_platforms"]
                    if "supported_platforms" in script.keys()
                    else list()
                )

                # if community script exists update it
                if s.exists():
                    i: Script = s.get()
                    i.name = script["name"]
                    i.description = script["description"]
                    i.category = category
                    i.shell = script["shell"]
                    i.default_timeout = default_timeout
                    i.args = args
                    i.syntax = syntax
                    i.filename = script["filename"]
                    i.supported_platforms = supported_platforms

                    with open(os.path.join(scripts_dir, script["filename"]), "rb") as f:
                        i.script_body = f.read().decode("utf-8")
                        # i.hash_script_body()
                        i.save()

                    community_scripts_processed.append(i.guid)

                # doesn't exist in database so create it
                else:
                    print(f"Adding new community script: {script['name']}")

                    with open(os.path.join(scripts_dir, script["filename"]), "rb") as f:
                        script_body = f.read().decode("utf-8")

                        new_script: Script = cls(
                            script_body=script_body,
                            guid=script["guid"],
                            name=script["name"],
                            description=script["description"],
                            shell=script["shell"],
                            script_type=ScriptType.BUILT_IN,
                            category=category,
                            default_timeout=default_timeout,
                            args=args,
                            filename=script["filename"],
                            syntax=syntax,
                            supported_platforms=supported_platforms,
                        )
                        # new_script.hash_script_body()  # also saves script
                        new_script.save()

                        community_scripts_processed.append(new_script.guid)

        # check for community scripts that were deleted from json and scripts folder
        count, _ = (
            Script.objects.filter(script_type=ScriptType.BUILT_IN)
            .exclude(guid__in=community_scripts_processed)
            .delete()
        )
        if count:
            print(
                f"Removing {count} community scripts that was removed from source repo"
            )

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
                value = replace_db_values(
                    string=string,
                    instance=agent,
                    shell=shell,
                    quotes=True if shell != ScriptShell.CMD else False,
                )

                if value:
                    temp_args.append(re.sub("\\{\\{.*\\}\\}", value, arg))
                else:
                    # pass parameter unaltered
                    temp_args.append(arg)

            else:
                temp_args.append(arg)

        return temp_args


class ScriptSnippet(models.Model):
    name = CharField(max_length=40, unique=True)
    desc = CharField(max_length=50, blank=True, default="")
    code = TextField(default="")
    shell = CharField(
        max_length=15, choices=ScriptShell.choices, default=ScriptShell.POWERSHELL
    )

    def __str__(self):
        return self.name
