import os

from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        # Only start the listener in the main process, not in worker processes
        if not settings.DEBUG or os.environ.get("RUN_MAIN") == "true":
            try:
                from core.agent_updater import start_listener

                # Start the agent update listener in the background
                start_listener(daemon=True)

            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to start agent update listener: {str(e)}")
