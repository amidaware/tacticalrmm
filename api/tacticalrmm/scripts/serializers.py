from rest_framework.serializers import ModelSerializer, ReadOnlyField

from .models import Script


class ScriptTableSerializer(ModelSerializer):
    class Meta:
        model = Script
        fields = [
            "id",
            "name",
            "description",
            "script_type",
            "shell",
            "category",
            "favorite",
        ]


class ScriptSerializer(ModelSerializer):
    class Meta:
        model = Script
        fields = [
            "id",
            "name",
            "description",
            "shell",
            "category",
            "favorite",
            "code_base64",
        ]


class ScriptCheckSerializer(ModelSerializer):
    code = ReadOnlyField()

    class Meta:
        model = Script
        fields = ["code", "shell"]
