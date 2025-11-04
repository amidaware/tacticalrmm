"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from django.urls import path

from . import views

urlpatterns = [
    path("branding/", views.AddBranding.as_view())
]