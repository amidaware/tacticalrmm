"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import urllib.parse
from time import sleep
from typing import Any, Optional

import requests
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

        attempts = 0
        while 1:
            try:
                r = requests.post(
                    settings.REPORTING_CHECK_URL,
                    json={"token": t.token, "api": settings.ALLOWED_HOSTS[0]},
                    headers={"Content-type": "application/json"},
                    timeout=15,
                )
            except Exception as e:
                self.stderr.write(str(e))
                attempts += 1
                sleep(3)
            else:
                if r.status_code // 100 in (3, 5):
                    self.stderr.write(f"Error getting web tarball: {r.status_code}")
                    attempts += 1
                    sleep(3)
                else:
                    attempts = 0

            if attempts == 0:
                break
            elif attempts > 5:
                self.stdout.write(url)
                return

        if r.status_code == 200:  # type: ignore
            params = {
                "token": t.token,
                "webver": settings.WEB_VERSION,
                "api": settings.ALLOWED_HOSTS[0],
            }
            url = settings.REPORTING_DL_URL + urllib.parse.urlencode(params)

        self.stdout.write(url)
