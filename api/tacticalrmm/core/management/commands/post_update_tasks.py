from time import sleep

from django.core.management.base import BaseCommand

from agents.models import Agent


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, after migrations"

    def handle(self, *args, **kwargs):
        # sync modules. split into chunks of 30 agents to not overload the salt master
        agents = Agent.objects.all()
        online = [i.salt_id for i in agents if i.status == "online"]

        chunks = (online[i : i + 30] for i in range(0, len(online), 30))

        self.stdout.write(self.style.SUCCESS("Syncing agent modules..."))
        for chunk in chunks:
            r = Agent.salt_batch_async(minions=chunk, func="saltutil.sync_modules")
            sleep(5)
