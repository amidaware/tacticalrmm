"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from django.conf import settings as djangosettings


class Settings:
    def __init__(self) -> None:
        self.settings = djangosettings

    @property
    def REPORTING_ASSETS_BASE_PATH(self) -> str:
        return getattr(
            self.settings,
            "REPORTING_ASSETS_BASE_PATH",
            "/opt/tactical/reporting/assets",
        )

    @property
    def REPORTING_BASE_URL(self) -> str:
        return getattr(
            self.settings,
            "REPORTING_BASE_URL",
            f"https://{djangosettings.ALLOWED_HOSTS[0]}",
        )


# import this to load initialized settings during runtime
settings = Settings()
