from django.db import models
from .utils import get_systray_assets_fs
from django.core.exceptions import ValidationError
import os


def validate_ico_file(value):
    ext = os.path.splitext(value.name)[1]
    if not ext.lower() == ".ico":
        raise ValidationError("Only .ico files are allowed.")


class SysTray(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    icon = models.FileField(
        storage=get_systray_assets_fs,
        blank=True,
        null=True,
        unique=True,
        validators=[validate_ico_file],
    )

    def __str__(self) -> str:
        return f"{self.name} = {self.icon}"
