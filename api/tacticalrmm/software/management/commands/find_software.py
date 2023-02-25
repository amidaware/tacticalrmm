from django.core.management.base import BaseCommand

from software.models import InstalledSoftware


class Command(BaseCommand):
    help = "Find all agents that have a certain software installed"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str)

    def handle(self, *args, **kwargs):
        search = kwargs["name"].lower()

        all_sw = InstalledSoftware.objects.select_related(
            "agent", "agent__site", "agent__site__client"
        )
        for instance in all_sw.iterator(chunk_size=20):
            for sw in instance.software:
                if search in sw["name"].lower():
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Found {sw['name']} installed on: {instance.agent.client.name}\\{instance.agent.site.name}\\{instance.agent.hostname}"
                        )
                    )
                    break
