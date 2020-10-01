from .models import Agent
from model_bakery.recipe import Recipe, seq
from model_bakery import baker
from itertools import cycle
import datetime as dt

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

online_agent = agent.extend(
    last_seen=dt.datetime.now()
)

overdue_agent = agent.extend(
    last_seen=dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=6)
)