from .models import Agent
from model_bakery.recipe import Recipe, seq
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
