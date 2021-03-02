import json
import os
import random
import string
from itertools import cycle

from django.conf import settings
from django.utils import timezone as djangotime
from model_bakery.recipe import Recipe, foreign_key, seq


def generate_agent_id(hostname):
    rand = "".join(random.choice(string.ascii_letters) for _ in range(35))
    return f"{rand}-{hostname}"


site = Recipe("clients.Site")


def get_wmi_data():
    with open(
        os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/wmi_python_agent.json")
    ) as f:
        return json.load(f)


agent = Recipe(
    "agents.Agent",
    site=foreign_key(site),
    hostname="DESKTOP-TEST123",
    version="1.3.0",
    monitoring_type=cycle(["workstation", "server"]),
    agent_id=seq("asdkj3h4234-1234hg3h4g34-234jjh34|DESKTOP-TEST123"),
)

server_agent = agent.extend(
    monitoring_type="server",
)

workstation_agent = agent.extend(
    monitoring_type="workstation",
)

online_agent = agent.extend(last_seen=djangotime.now())

offline_agent = agent.extend(
    last_seen=djangotime.now() - djangotime.timedelta(minutes=7)
)

overdue_agent = agent.extend(
    last_seen=djangotime.now() - djangotime.timedelta(minutes=35)
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
