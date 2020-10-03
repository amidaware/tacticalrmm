from .models import Agent
from model_bakery.recipe import Recipe, seq
from model_bakery import baker
from itertools import cycle
from django.utils import timezone as djangotime

agent = Recipe(
    Agent,
    client="Default",
    site="Default",
    hostname=seq("TestHostname"),
    monitoring_type=cycle(["workstation", "server"]),
)

server_agent = agent.extend(
    monitoring_type="server",
)

workstation_agent = agent.extend(
    monitoring_type="workstation",
)

online_agent = agent.extend(last_seen=djangotime.now())

overdue_agent = agent.extend(
    last_seen=djangotime.now() - djangotime.timedelta(minutes=6)
)