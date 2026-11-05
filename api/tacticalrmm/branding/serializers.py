from django.core.validators import RegexValidator
from rest_framework import serializers

from .models import BrandingSettings

COLOR_FIELDS = ("primary", "secondary", "accent", "header", "dark_primary", "dark_page")

hex_color = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Use the format #RRGGBB.")


class BrandingSerializer(serializers.ModelSerializer):
    has_logo = serializers.SerializerMethodField()
    has_favicon = serializers.SerializerMethodField()
    has_login_background = serializers.SerializerMethodField()
    version = serializers.ReadOnlyField()

    class Meta:
        model = BrandingSettings
        fields = [
            "product_name",
            *COLOR_FIELDS,
            "has_logo",
            "has_favicon",
            "has_login_background",
            "version",
        ]
        extra_kwargs = {field: {"validators": [hex_color]} for field in COLOR_FIELDS}

    def get_has_logo(self, obj) -> bool:
        return obj.has_image("logo")

    def get_has_favicon(self, obj) -> bool:
        return obj.has_image("favicon")

    def get_has_login_background(self, obj) -> bool:
        return obj.has_image("login_background")
