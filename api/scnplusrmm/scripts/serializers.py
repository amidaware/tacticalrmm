from rest_framework.serializers import ModelSerializer, ReadOnlyField

from .models import Script, ScriptSnippet


class ScriptTableSerializer(ModelSerializer):
    class Meta:
        model = Script
        fields = [
            "id",
            "name",
            "description",
            "script_type",
            "shell",
            "args",
            "category",
            "favorite",
            "default_timeout",
            "syntax",
            "filename",
            "hidden",
            "supported_platforms",
            "run_as_user",
            "env_vars",
        ]


class ScriptSerializer(ModelSerializer):
    script_hash = ReadOnlyField()

    class Meta:
        model = Script
        fields = [
            "id",
            "name",
            "description",
            "shell",
            "args",
            "category",
            "favorite",
            "script_body",
            "script_hash",
            "default_timeout",
            "syntax",
            "filename",
            "hidden",
            "supported_platforms",
            "run_as_user",
            "env_vars",
        ]
        extra_kwargs = {"script_body": {"trim_whitespace": False}}


class ScriptCheckSerializer(ModelSerializer):
    code = ReadOnlyField()
    script_hash = ReadOnlyField()

    class Meta:
        model = Script
        fields = ["code", "shell", "run_as_user", "env_vars", "script_hash"]


class ScriptSnippetSerializer(ModelSerializer):
    class Meta:
        model = ScriptSnippet
        fields = "__all__"
        extra_kwargs = {"code": {"trim_whitespace": False}}
