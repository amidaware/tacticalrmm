from django.core.management.base import BaseCommand

from agents.models import Agent
from tacticalrmm.constants import AGENT_DEFER


class Command(BaseCommand):
    def find_duplicates(self, lst):
        return list(set([item for item in lst if lst.count(item) > 1]))

    def handle(self, *args, **kwargs):
        for agent in Agent.objects.defer(*AGENT_DEFER).prefetch_related(
            "custom_fields__field"
        ):
            if dupes := self.find_duplicates(
                [i.field.name for i in agent.custom_fields.all()]
            ):
                for dupe in dupes:
                    cf = list(
                        agent.custom_fields.filter(field__name=dupe).order_by("id")
                    )
                    to_delete = cf[:-1]
                    for i in to_delete:
                        i.delete()
