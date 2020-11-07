import random
import string
import os
import json

from model_bakery.recipe import Recipe, seq
from itertools import cycle
from django.utils import timezone as djangotime
from django.conf import settings

from .models import Agent


def generate_agent_id(hostname):
    rand = "".join(random.choice(string.ascii_letters) for _ in range(35))
    return f"{rand}-{hostname}"


def get_wmi_data():
    with open(
        os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/wmi_python_agent.json")
    ) as f:
        return json.load(f)


agent = Recipe(
    Agent,
    hostname="DESKTOP-TEST123",
    monitoring_type=cycle(["workstation", "server"]),
    salt_id=generate_agent_id("DESKTOP-TEST123"),
    agent_id="71AHC-AA813-HH1BC-AAHH5-00013|DESKTOP-TEST123",
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

agent_with_services = agent.extend(
    services=[
        {
            "pid": 880,
            "name": "AeLookupSvc",
            "status": "stopped",
            "binpath": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
            "username": "localSystem",
            "start_type": "manual",
            "description": "Processes application compatibility cache requests for applications as they are launched",
            "display_name": "Application Experience",
        },
        {
            "pid": 812,
            "name": "ALG",
            "status": "stopped",
            "binpath": "C:\\Windows\\System32\\alg.exe",
            "username": "NT AUTHORITY\\LocalService",
            "start_type": "manual",
            "description": "Provides support for 3rd party protocol plug-ins for Internet Connection Sharing",
            "display_name": "Application Layer Gateway Service",
        },
    ],
)

agent_with_wmi = agent.extend(wmi=get_wmi_data())
