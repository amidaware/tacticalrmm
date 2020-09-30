from .models import Agent
from model_bakery.recipe import Recipe, seq
from itertools import cycle

agent = Recipe(Agent, client="Default", site="Default", hostname="TestHostname")

server_agent = Recipe(
    Agent,
    monitoring_mode="server",
    client="Default",
    site="Default",
    hostname="ServerHost",
)

workstation_agent = Recipe(
    Agent,
    monitoring_mode="server",
    client="Default",
    site="Default",
    hostname="WorkstationHost",
)
