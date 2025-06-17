"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from django.contrib import admin

from .models import (
    ReportAsset,
    ReportTemplate,
    ReportDataQuery,
    ReportSchedule,
    ReportHistory,
)

admin.site.register(ReportTemplate)
admin.site.register(ReportAsset)
admin.site.register(ReportDataQuery)
admin.site.register(ReportSchedule)
admin.site.register(ReportHistory)
