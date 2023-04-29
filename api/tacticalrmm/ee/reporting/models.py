"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from django.db import models
import uuid
from .storage import report_assets_fs


class ReportFormatType(models.TextChoices):
    MARKDOWN = "markdown", "Markdown"
    HTML = "html", "Html"


class ReportTemplate(models.Model):
    name = models.CharField(max_length=50, unique=True)
    template_md = models.TextField()
    template_css = models.TextField(null=True, blank=True)
    template_html = models.ForeignKey(
        "ReportHTMLTemplate",
        related_name="htmltemplate",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )
    type = models.CharField(
        max_length=15,
        choices=ReportFormatType.choices,
        default=ReportFormatType.MARKDOWN,
    )

    def __str__(self) -> str:
        return self.name


class ReportHTMLTemplate(models.Model):
    name = models.CharField(max_length=50, unique=True)
    html = models.TextField()

    def __str__(self) -> str:
        return self.name


class ReportAsset(models.Model):
    id = models.UUIDField(
        primary_key=True, unique=True, default=uuid.uuid4, editable=False
    )
    file = models.FileField(storage=report_assets_fs, unique=True)

    def __str__(self) -> str:
        return f"{self.id} - {self.file}"


class ReportDataQuery(models.Model):
    name = models.CharField(max_length=50, unique=True)
    json_query = models.JSONField()
