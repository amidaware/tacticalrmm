import json
import os
import secrets
import string
from itertools import cycle

from django.conf import settings
from django.utils import timezone as djangotime
from model_bakery.recipe import Recipe, foreign_key, seq

from tacticalrmm.constants import AgentMonType, AgentPlat


def generate_agent_id() -> str:
    return "".join(secrets.choice(string.ascii_letters) for i in range(39))


site = Recipe("clients.Site")


def get_wmi_data():
    with open(
        os.path.join(settings.BASE_DIR, "tacticalrmm/test_data/wmi_python_agent.json")
    ) as f:
        return json.load(f)


def get_win_svcs():
    svcs = settings.BASE_DIR.joinpath("tacticalrmm/test_data/winsvcs.json")
    with open(svcs) as f:
        return json.load(f)


agent = Recipe(
    "agents.Agent",
    site=foreign_key(site),
    hostname="DESKTOP-TEST123",
    version="1.3.0",
    monitoring_type=cycle(AgentMonType.values),
    agent_id=seq(generate_agent_id()),
    last_seen=djangotime.now() - djangotime.timedelta(days=5),
    plat=AgentPlat.WINDOWS,
)

server_agent = agent.extend(
    monitoring_type=AgentMonType.SERVER,
)

workstation_agent = agent.extend(
    monitoring_type=AgentMonType.WORKSTATION,
)

online_agent = agent.extend(
    last_seen=djangotime.now(), services=get_win_svcs(), wmi_detail=get_wmi_data()
)

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

agent_with_wmi = agent.extend(wmi_detail=get_wmi_data())
