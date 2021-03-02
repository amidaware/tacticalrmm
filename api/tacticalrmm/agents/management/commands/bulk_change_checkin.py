from django.core.management.base import BaseCommand

from agents.models import Agent
from clients.models import Client, Site


class Command(BaseCommand):
    help = "Bulk update agent offline/overdue time"

    def add_arguments(self, parser):
        parser.add_argument("time", type=int, help="Time in minutes")
        parser.add_argument(
            "--client",
            type=str,
            help="Client Name",
        )
        parser.add_argument(
            "--site",
            type=str,
            help="Site Name",
        )
        parser.add_argument(
            "--offline",
            action="store_true",
            help="Offline",
        )
        parser.add_argument(
            "--overdue",
            action="store_true",
            help="Overdue",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="All agents",
        )

    def handle(self, *args, **kwargs):
        time = kwargs["time"]
        client_name = kwargs["client"]
        site_name = kwargs["site"]
        all_agents = kwargs["all"]
        offline = kwargs["offline"]
        overdue = kwargs["overdue"]
        agents = None

        if offline and time < 2:
            self.stdout.write(self.style.ERROR("Minimum offline time is 2 minutes"))
            return

        if overdue and time < 3:
            self.stdout.write(self.style.ERROR("Minimum overdue time is 3 minutes"))
            return

        if client_name:
            try:
                client = Client.objects.get(name=client_name)
            except Client.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Client {client_name} doesn't exist")
                )
                return

            agents = Agent.objects.filter(site__client=client)

        elif site_name:
            try:
                site = Site.objects.get(name=site_name)
            except Site.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Site {site_name} doesn't exist"))
                return

            agents = Agent.objects.filter(site=site)

        elif all_agents:
            agents = Agent.objects.all()

        if agents:
            if offline:
                agents.update(offline_time=time)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Changed offline time on {len(agents)} agents to {time} minutes"
                    )
                )

            if overdue:
                agents.update(overdue_time=time)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Changed overdue time on {len(agents)} agents to {time} minutes"
                    )
                )
