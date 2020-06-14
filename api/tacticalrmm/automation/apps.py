from django.apps import AppConfig


class AutomationConfig(AppConfig):
    name = "automation"

    def ready(self):

        # registering signals defined in signals.py
        import automation.signals
