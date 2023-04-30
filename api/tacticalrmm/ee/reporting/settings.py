"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from django.conf import settings as djangosettings


class Settings:
    def __init__(self) -> None:
        self.settings = djangosettings

    # settings for trmm readonly database account
    @property
    def REPORTING_CONNECTION_NAME(self) -> str:
        return getattr(self.settings, "REPORTING_DB_CONNECTION_NAME", "reporting")

    @property
    def REPORTING_DB_NAME(self) -> str:
        return getattr(self.settings, "REPORTING_DB_NAME", "tacticalrmm")

    @property
    def REPORTING_DB_HOST(self) -> str:
        return getattr(self.settings, "REPORTING_DB_HOST", "localhost")

    @property
    def REPORTING_DB_PORT(self) -> str:
        return getattr(self.settings, "REPORTING_DB_PORT", "5432")

    @property
    def REPORTING_DB_USER(self) -> str:
        return getattr(self.settings, "REPORTING_DB_USER", "reporting_user")

    @property
    def REPORTING_DB_PASSWORD(self) -> str:
        return getattr(self.settings, "REPORTING_DB_PASSWORD", "reporting_password")

    @property
    def REPORTING_ASSETS_BASE_PATH(self) -> str:
        return getattr(
            self.settings,
            "REPORTING_ASSETS_BASE_PATH",
            "/opt/tactical/reporting",
        )

    @property
    def REPORTING_BASE_URL(self) -> str:
        return getattr(
            self.settings,
            "REPORTING_BASE_URL",
            f"https://{djangosettings.ALLOWED_HOSTS[0]}/assets",
        )


# import this to load initialized settings during runtime
settings = Settings()
