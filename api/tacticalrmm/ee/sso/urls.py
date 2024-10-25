"""
Copyright (c) 2024-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from django.urls import path, include, re_path
from allauth.socialaccount.providers.openid_connect.views import callback
from allauth.headless.socialaccount.views import RedirectToProviderView
from allauth.headless.base.views import ConfigView

from . import views

urlpatterns = [
    re_path(
        r"^oidc/(?P<provider_id>[^/]+)/",
        include(
            [
                path(
                    "login/callback/",
                    callback,
                    name="openid_connect_callback",
                ),
            ]
        ),
    ),
    path("ssoproviders/", views.GetAddSSOProvider.as_view()),
    path("ssoproviders/<int:pk>/", views.GetUpdateDeleteSSOProvider.as_view()),
    path("ssoproviders/token/", views.GetAccessToken.as_view()),
    path("ssoproviders/settings/", views.GetUpdateSSOSettings.as_view()),
    path("ssoproviders/account/", views.DisconnectSSOAccount.as_view()),
]

allauth_urls = [
    path(
        "browser/v1/",
        include(
            (
                [
                    path(
                        "config/",
                        ConfigView.as_api_view(client="browser"),
                        name="config",
                    ),
                    path(
                        "",
                        include(
                            (
                                [
                                    path(
                                        "auth/provider/redirect/",
                                        RedirectToProviderView.as_api_view(
                                            client="browser"
                                        ),
                                        name="redirect_to_provider",
                                    )
                                ],
                                "headless",
                            ),
                            namespace="socialaccount",
                        ),
                    ),
                ],
                "headless",
            ),
            namespace="browser",
        ),
    )
]
