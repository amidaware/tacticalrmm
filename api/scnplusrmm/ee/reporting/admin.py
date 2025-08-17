"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from django.contrib import admin

from .models import ReportAsset, ReportTemplate

admin.site.register(ReportTemplate)
admin.site.register(ReportAsset)
