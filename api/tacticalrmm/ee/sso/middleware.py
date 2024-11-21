"""
Copyright (c) 2024-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import json
from contextlib import suppress

from allauth.headless.base.response import ConfigResponse
from allauth.socialaccount.models import SocialApp


def set_provider_icon(provider, url):
    icon_map = {
        "google.com": "mdi-google",
        "microsoft": "mdi-microsoft",
        "discord.com": "fa-brands fa-discord",
        "github.com": "fa-brands fa-github",
        "slack.com": "fa-brands fa-slack",
        "facebook.com": "fa-brands fa-facebook",
        "linkedin.com": "fa-brands fa-linkedin",
        "apple.com": "fa-brands fa-apple",
        "amazon.com": "fa-brands fa-amazon",
        "auth0.com": "mdi-lock",
        "gitlab.com": "fa-brands fa-gitlab",
        "twitter.com": "fa-brands fa-twitter",
        "paypal.com": "fa-brands fa-paypal",
        "yahoo.com": "fa-brands fa-yahoo",
    }

    provider["icon"] = "mdi-key"

    for key, icon in icon_map.items():
        if key in url.lower():
            provider["icon"] = icon
            break


class SSOIconMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path == "/_allauth/browser/v1/config/" and isinstance(
            response, ConfigResponse
        ):
            with suppress(Exception):
                data = json.loads(response.content.decode("utf-8", "ignore"))

                data["data"].pop("account", None)
                for provider in data["data"]["socialaccount"].get("providers", []):
                    provider.pop("client_id", None)
                    provider.pop("flows", None)
                    app = SocialApp.objects.get(provider_id=provider["id"])
                    set_provider_icon(provider, app.settings["server_url"])

                new_content = json.dumps(data)
                response.content = new_content.encode("utf-8", "ignore")
                response["Content-Length"] = str(len(response.content))

        return response
