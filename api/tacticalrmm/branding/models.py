from django.core.exceptions import ValidationError
from django.db import models

from logs.models import BaseAuditModel

IMAGE_KINDS = ("logo", "favicon", "login_background")


class BrandingSettings(BaseAuditModel):
    # empty values mean "use the built-in default"
    product_name = models.CharField(max_length=100, blank=True, default="")
    primary = models.CharField(max_length=7, blank=True, default="")
    secondary = models.CharField(max_length=7, blank=True, default="")
    accent = models.CharField(max_length=7, blank=True, default="")
    header = models.CharField(max_length=7, blank=True, default="")
    dark_primary = models.CharField(max_length=7, blank=True, default="")
    dark_page = models.CharField(max_length=7, blank=True, default="")
    logo = models.BinaryField(null=True, blank=True)
    logo_type = models.CharField(max_length=50, blank=True, default="")
    favicon = models.BinaryField(null=True, blank=True)
    favicon_type = models.CharField(max_length=50, blank=True, default="")
    login_background = models.BinaryField(null=True, blank=True)
    login_background_type = models.CharField(max_length=50, blank=True, default="")

    def __str__(self) -> str:
        return "Branding Settings"

    def save(self, *args, **kwargs) -> None:
        if not self.pk and BrandingSettings.objects.exists():
            raise ValidationError("There can only be one BrandingSettings instance")

        super().save(*args, **kwargs)

    @staticmethod
    def serialize(branding):
        from .serializers import BrandingSerializer

        return BrandingSerializer(branding).data

    @property
    def version(self) -> int:
        # used by the frontend to bust the browser cache of images
        if not self.modified_time:
            return 0
        return int(self.modified_time.timestamp() * 1000)

    def has_image(self, kind: str) -> bool:
        return bool(getattr(self, kind))


def get_branding() -> BrandingSettings:
    return BrandingSettings.objects.first() or BrandingSettings()
