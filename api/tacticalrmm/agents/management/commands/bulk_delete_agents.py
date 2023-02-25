import asyncio

from django.core.management.base import BaseCommand
from django.utils import timezone as djangotime
from packaging import version as pyver

from agents.models import Agent
from tacticalrmm.constants import AGENT_DEFER
from tacticalrmm.utils import reload_nats


class Command(BaseCommand):
    help = "Delete multiple agents based on criteria"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            help="Delete agents that have not checked in for this many days",
        )
        parser.add_argument(
            "--agentver",
            type=str,
            help="Delete agents that equal to or less than this version",
        )
        parser.add_argument(
            "--site",
            type=str,
            help="Delete agents that belong to the specified site",
        )
        parser.add_argument(
            "--client",
            type=str,
            help="Delete agents that belong to the specified client",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="This will delete agents",
        )

    def handle(self, *args, **kwargs):
        days = kwargs["days"]
        agentver = kwargs["agentver"]
        site = kwargs["site"]
        client = kwargs["client"]
        delete = kwargs["delete"]

        if not days and not agentver and not site and not client:
            self.stdout.write(
                self.style.ERROR(
                    "Must have at least one parameter: days, agentver, site, or client"
                )
            )
            return

        q = Agent.objects.defer(*AGENT_DEFER)

        agents = []
        if days:
            overdue = djangotime.now() - djangotime.timedelta(days=days)
            agents = [i for i in q if i.last_seen < overdue]

        if agentver:
            agents = [i for i in q if pyver.parse(i.version) <= pyver.parse(agentver)]

        if site:
            agents = [i for i in q if i.site.name == site]

        if client:
            agents = [i for i in q if i.client.name == client]

        if not agents:
            self.stdout.write(self.style.ERROR("No agents matched"))
            return

        deleted_count = 0
        for agent in agents:
            s = f"{agent.hostname} | Version {agent.version} | Last Seen {agent.last_seen} | {agent.client} > {agent.site}"
            if delete:
                s = "Deleting " + s
                self.stdout.write(self.style.SUCCESS(s))
                asyncio.run(agent.nats_cmd({"func": "uninstall"}, wait=False))
                try:
                    agent.delete()
                except Exception as e:
                    err = f"Failed to delete agent {agent.hostname}: {e}"
                    self.stdout.write(self.style.ERROR(err))
                else:
                    deleted_count += 1
            else:
                self.stdout.write(self.style.WARNING(s))

        if delete:
            reload_nats()
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} agents"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "The above agents would be deleted. Run again with --delete to actually delete them."
                )
            )
