import os

from rest_framework.serializers import ModelSerializer, ValidationError, ReadOnlyField
from .models import Script


class ScriptSerializer(ModelSerializer):

    code = ReadOnlyField()
    filepath = ReadOnlyField()

    class Meta:
        model = Script
        fields = "__all__"

    def validate(self, val):
        if "filename" in val:
            # validate the filename
            if (
                not val["filename"].endswith(".py")
                and not val["filename"].endswith(".ps1")
                and not val["filename"].endswith(".bat")
            ):
                raise ValidationError("File types supported are .py, .ps1 and .bat")

            # make sure file doesn't already exist on server
            # but only if adding, not if editing since will overwrite if edit
            if not self.instance:
                script_path = os.path.join(
                    "/srv/salt/scripts/userdefined", val["filename"]
                )
                if os.path.exists(script_path):
                    raise ValidationError(
                        f"{val['filename']} already exists. Delete or edit the existing script first."
                    )

        return val


class ScriptCheckSerializer(ModelSerializer):
    code = ReadOnlyField()

    class Meta:
        model = Script
        fields = ["code", "shell"]
