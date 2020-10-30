from django.apps import AppConfig


class AutotasksConfig(AppConfig):
    name = "autotasks"

    def ready(self):
        from . import signals
