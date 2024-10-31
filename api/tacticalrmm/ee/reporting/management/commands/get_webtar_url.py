"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import urllib.parse
from typing import Any, Optional

from core.models import CodeSignToken
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Get webtar url"

    def handle(self, *args: tuple[Any, Any], **kwargs: dict[str, Any]) -> None:
        webtar = f"trmm-web-v{settings.WEB_VERSION}.tar.gz"
        url = f"https://github.com/amidaware/tacticalrmm-web/releases/download/v{settings.WEB_VERSION}/{webtar}"

        t: "Optional[CodeSignToken]" = CodeSignToken.objects.first()
        if not t or not t.token:
            self.stdout.write(url)
            return

        if t.is_valid:
            params = {
                "token": t.token,
                "webver": settings.WEB_VERSION,
                "api": settings.ALLOWED_HOSTS[0],
            }
            url = settings.WEBTAR_DL_URL + urllib.parse.urlencode(params)

        self.stdout.write(url)
