import os
import shutil
import subprocess
import tempfile

from django.core.management.base import BaseCommand

from agents.models import Agent
from scripts.models import Script


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, after migrations"

    def handle(self, *args, **kwargs):
        # 10-16-2020 changed the type of the agent's 'disks' model field
        # from a dict of dicts, to a list of disks in the golang agent
        # the following will convert dicts to lists for agent's still on the python agent
        agents = Agent.objects.only("pk", "disks")
        for agent in agents:
            if agent.disks is not None and isinstance(agent.disks, dict):
                new = []
                for k, v in agent.disks.items():
                    new.append(v)

                agent.disks = new
                agent.save(update_fields=["disks"])
                self.stdout.write(
                    self.style.SUCCESS(f"Migrated disks on {agent.hostname}")
                )

        # load community scripts into the db
        Script.load_community_scripts()
