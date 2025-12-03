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
from tacticalrmm.utils import get_webtar_url

class Command(BaseCommand):
    help = "Get webtar url"

    def handle(self, *args: tuple[Any, Any], **kwargs: dict[str, Any]) -> None:
        self.stdout.write(get_webtar_url())
