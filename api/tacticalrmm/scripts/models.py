import hashlib
import hmac
import re
from typing import List

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.fields import CharField, TextField

from logs.models import BaseAuditModel
from tacticalrmm.constants import ScriptShell, ScriptType
from tacticalrmm.utils import replace_arg_db_values


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
    env_vars = ArrayField(
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
    run_as_user = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def code_no_snippets(self):
        return self.script_body or ""

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
                    replaced_code = re.sub(
                        snippet.group(), value.replace("\\", "\\\\"), replaced_code
                    )
            return replaced_code

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

                args = script["args"] if "args" in script.keys() else []

                env = script["env"] if "env" in script.keys() else []

                syntax = script["syntax"] if "syntax" in script.keys() else ""

                run_as_user = (
                    script["run_as_user"] if "run_as_user" in script.keys() else False
                )

                supported_platforms = (
                    script["supported_platforms"]
                    if "supported_platforms" in script.keys()
                    else []
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
                    i.env_vars = env
                    i.syntax = syntax
                    i.run_as_user = run_as_user
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
                            env_vars=env,
                            filename=script["filename"],
                            syntax=syntax,
                            run_as_user=run_as_user,
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
    # TODO refactor common functionality of parse functions
    def parse_script_args(cls, agent, shell: str, args: List[str] = []) -> list:
        if not args:
            return []

        temp_args = []

        # pattern to match for injection
        pattern = re.compile(".*\\{\\{(.*)\\}\\}.*")

        for arg in args:
            if match := pattern.match(arg):
                # only get the match between the () in regex
                string = match.group(1)
                value = replace_arg_db_values(
                    string=string,
                    instance=agent,
                    shell=shell,
                    quotes=shell != ScriptShell.CMD,
                )

                if value:
                    try:
                        temp_args.append(re.sub("\\{\\{.*\\}\\}", value, arg))
                    except re.error:
                        temp_args.append(
                            re.sub("\\{\\{.*\\}\\}", re.escape(value), arg)
                        )
                else:
                    # pass parameter unaltered
                    temp_args.append(arg)

            else:
                temp_args.append(arg)

        return temp_args

    @classmethod
    # TODO refactor common functionality of parse functions
    def parse_script_env_vars(cls, agent, shell: str, env_vars: list[str] = []) -> list:
        if not env_vars:
            return []

        temp_env_vars = []
        pattern = re.compile(".*\\{\\{(.*)\\}\\}.*")
        for env_var in env_vars:
            # must be in format KEY=VALUE
            try:
                env_key = env_var.split("=")[0]
                env_val = env_var.split("=")[1]
            except:
                continue
            if match := pattern.match(env_val):
                string = match.group(1)
                value = replace_arg_db_values(
                    string=string,
                    instance=agent,
                    shell=shell,
                    quotes=False,
                )

                if value:
                    try:
                        new_val = re.sub("\\{\\{.*\\}\\}", value, env_val)
                    except re.error:
                        new_val = re.sub("\\{\\{.*\\}\\}", re.escape(value), env_val)
                    temp_env_vars.append(f"{env_key}={new_val}")
            else:
                # pass parameter unaltered
                temp_env_vars.append(env_var)

        return temp_env_vars


class ScriptSnippet(models.Model):
    name = CharField(max_length=40, unique=True)
    desc = CharField(max_length=50, blank=True, default="")
    code = TextField(default="")
    shell = CharField(
        max_length=15, choices=ScriptShell.choices, default=ScriptShell.POWERSHELL
    )

    def __str__(self):
        return self.name
