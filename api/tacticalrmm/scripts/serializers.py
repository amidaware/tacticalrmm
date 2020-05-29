from rest_framework import serializers
from .models import Script


class ScriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Script
        fields = "__all__"

    def validate_filename(self, val):
        if (
            not val.endswith(".py")
            and not val.endswith(".ps1")
            and not val.endswith(".bat")
        ):
            raise serializers.ValidationError(
                "File types supported are .py, .ps1 and .bat"
            )
        return val
