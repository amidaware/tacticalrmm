"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

   
from django.urls import path
from django.urls import include

from . import views

urlpatterns = [
    path("", include("allauth.urls")),
    path("ssoproviders/", views.GetAddSSOProvider.as_view()),
    path("ssoproviders/<int:pk>/", views.GetUpdateDeleteSSOProvider.as_view()),
    path("ssoproviders/token/", views.GetAccessToken.as_view()),
    path("ssoproviders/settings/", views.GetUpdateSSOSettings.as_view()),
]