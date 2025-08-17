import json
import os

from django.core.management.base import BaseCommand

from agents.models import Agent


class Command(BaseCommand):
    help = "Toggle server maintenance mode, preserving existing state"

    def add_arguments(self, parser):
        parser.add_argument("--enable", action="store_true")
        parser.add_argument("--disable", action="store_true")
        parser.add_argument("--force-enable", action="store_true")
        parser.add_argument("--force-disable", action="store_true")

    def handle(self, *args, **kwargs):
        enable = kwargs["enable"]
        disable = kwargs["disable"]
        force_enable = kwargs["force_enable"]
        force_disable = kwargs["force_disable"]

        home_dir = os.path.expanduser("~")
        fp = os.path.join(home_dir, "agents_maint_mode.json")

        if enable:
            current = list(
                Agent.objects.filter(maintenance_mode=True).values_list("id", flat=True)
            )

            with open(fp, "w") as f:
                json.dump(current, f)

            Agent.objects.update(maintenance_mode=True)

        elif disable:
            with open(fp, "r") as f:
                state = json.load(f)

            Agent.objects.exclude(pk__in=state).update(maintenance_mode=False)

        elif force_enable:
            Agent.objects.update(maintenance_mode=True)

        elif force_disable:
            if os.path.exists(fp):
                os.remove(fp)

            Agent.objects.update(maintenance_mode=False)
