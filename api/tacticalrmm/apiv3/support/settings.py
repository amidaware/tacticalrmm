from django.conf import settings as djangosettings

class Settings:
    def __init__(self) -> None:
        self.settings = djangosettings

    @property
    def SYSTRAY_ASSETS_BASE_PATH(self) -> str:
        return getattr(
            self.settings,
            "SYSTRAY_ASSETS_BASE_PATH",
            "/rmm/api/tacticalrmm/tacticalrmm/private/assets/",
        )

    @property
    def SYSTRAY_BASE_URL(self) -> str:
        return getattr(
            self.settings,
            "SYSTRAY_BASE_URL",
            f"https://{djangosettings.ALLOWED_HOSTS[0]}",
        )


settings = Settings()