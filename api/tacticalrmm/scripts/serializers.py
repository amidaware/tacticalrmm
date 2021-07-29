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
        ]


class ScriptSerializer(ModelSerializer):
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
            "code_base64",
            "default_timeout",
        ]


class ScriptCheckSerializer(ModelSerializer):
    code = ReadOnlyField()

    class Meta:
        model = Script
        fields = ["code", "shell"]


class ScriptSnippetSerializer(ModelSerializer):
    class Meta:
        model = ScriptSnippet
        fields = "__all__"