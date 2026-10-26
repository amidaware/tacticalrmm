from django.apps import AppConfig


class AgentsConfig(AppConfig):
    name = "agents"

    def ready(self) -> None:
        # Register file-transfer system checks.
        from . import checks  # noqa: F401
