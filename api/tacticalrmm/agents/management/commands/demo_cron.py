# import datetime as dt
import random

from django.core.management.base import BaseCommand
from django.utils import timezone as djangotime

from agents.models import Agent
from core.tasks import cache_db_fields_task


class Command(BaseCommand):
    help = "stuff for demo site in cron"

    def handle(self, *args, **kwargs):
        random_dates = []
        now = djangotime.now()

        for _ in range(20):
            rand = now - djangotime.timedelta(minutes=random.randint(1, 2))
            random_dates.append(rand)

        for _ in range(5):
            rand = now - djangotime.timedelta(minutes=random.randint(10, 20))
            random_dates.append(rand)

        agents = Agent.objects.only("last_seen")
        for agent in agents:
            agent.last_seen = random.choice(random_dates)
            agent.save(update_fields=["last_seen"])

        cache_db_fields_task()
