"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models
from logs.models import BaseAuditModel
from .storage import get_report_assets_fs


class ReportFormatType(models.TextChoices):
    MARKDOWN = "markdown", "Markdown"
    HTML = "html", "Html"
    PLAIN_TEXT = "plaintext", "Plain Text"


class ReportTemplate(BaseAuditModel):
    name = models.CharField(max_length=200, unique=True)
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
    template_variables = models.TextField(blank=True, default="")
    depends_on = ArrayField(
        models.CharField(max_length=20, blank=True), blank=True, default=list
    )

    def __str__(self) -> str:
        return self.name


class ReportHTMLTemplate(BaseAuditModel):
    name = models.CharField(max_length=200, unique=True)
    html = models.TextField()

    def __str__(self) -> str:
        return self.name


class ReportAsset(BaseAuditModel):
    id = models.UUIDField(
        primary_key=True, unique=True, default=uuid.uuid4, editable=False
    )
    file = models.FileField(storage=get_report_assets_fs, unique=True)

    def __str__(self) -> str:
        return f"{self.id} - {self.file}"


class ReportDataQuery(BaseAuditModel):
    name = models.CharField(max_length=50, unique=True)
    json_query = models.JSONField()

    def __str__(self) -> str:
        return self.name


class ReportRunFormat(models.TextChoices):
    PDF = "pdf", "Pdf"
    HTML = "html", "Html"
    PLAINTEXT = "plaintext", "Plain Text"


class ReportSchedule(BaseAuditModel):

    name = models.CharField(
        max_length=255,
    )
    enabled = models.BooleanField(default=True)
    report_template = models.ForeignKey(
        "ReportTemplate",
        related_name="reporttemplate_schedules",
        on_delete=models.CASCADE,
    )

    format = models.CharField(
        max_length=10,
        choices=ReportRunFormat.choices,
        default=ReportRunFormat.HTML,
    )

    schedule = models.ForeignKey(
        "core.Schedule",
        related_name="schedule",
        on_delete=models.DO_NOTHING,
    )

    dependencies = models.JSONField(default=dict)
    email_recipients = ArrayField(
        base_field=models.EmailField(),
        blank=True,
        default=list,
    )
    no_email = models.BooleanField(default=False)
    last_run = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class ReportHistory(BaseAuditModel):
    report_template = models.ForeignKey(
        "ReportTemplate",
        related_name="reporttemplate_history",
        on_delete=models.CASCADE,
    )
    run_by = models.CharField(max_length=255, default="system")
    report_data = models.TextField()
    error_data = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report_template} - {self.date_created}"
