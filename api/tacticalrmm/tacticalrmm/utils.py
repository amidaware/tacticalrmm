import json
import os
import string
import subprocess
from typing import List, Dict
from loguru import logger

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

from agents.models import Agent

logger.configure(**settings.LOG_CONFIG)

notify_error = lambda msg: Response(msg, status=status.HTTP_400_BAD_REQUEST)

SoftwareList = List[Dict[str, str]]

WEEK_DAYS = {
    "Sunday": 0x1,
    "Monday": 0x2,
    "Tuesday": 0x4,
    "Wednesday": 0x8,
    "Thursday": 0x10,
    "Friday": 0x20,
    "Saturday": 0x40,
}


def get_bit_days(days: List[str]) -> int:
    bit_days = 0
    for day in days:
        bit_days |= WEEK_DAYS.get(day)
    return bit_days


def bitdays_to_string(day: int) -> str:
    ret = []
    if day == 127:
        return "Every day"

    if day & WEEK_DAYS["Sunday"]:
        ret.append("Sunday")
    if day & WEEK_DAYS["Monday"]:
        ret.append("Monday")
    if day & WEEK_DAYS["Tuesday"]:
        ret.append("Tuesday")
    if day & WEEK_DAYS["Wednesday"]:
        ret.append("Wednesday")
    if day & WEEK_DAYS["Thursday"]:
        ret.append("Thursday")
    if day & WEEK_DAYS["Friday"]:
        ret.append("Friday")
    if day & WEEK_DAYS["Saturday"]:
        ret.append("Saturday")

    return ", ".join(ret)

def filter_software(sw: SoftwareList) -> SoftwareList:
    ret: SoftwareList = []
    printable = set(string.printable)
    for s in sw:
        ret.append(
            {
                "name": "".join(filter(lambda x: x in printable, s["name"])),
                "version": "".join(filter(lambda x: x in printable, s["version"])),
                "publisher": "".join(filter(lambda x: x in printable, s["publisher"])),
                "install_date": s["install_date"],
                "size": s["size"],
                "source": s["source"],
                "location": s["location"],
                "uninstall": s["uninstall"],
            }
        )
    
    return ret

def reload_nats():
    users = [{"user": "tacticalrmm", "password": settings.SECRET_KEY}]
    agents = Agent.objects.prefetch_related("user").only("pk", "agent_id")
    for agent in agents:
        try:
            users.append(
                {"user": agent.agent_id, "password": agent.user.auth_token.key}
            )
        except:
            logger.critical(
                f"{agent.hostname} does not have a user account, NATS will not work"
            )

    if not settings.DOCKER_BUILD:
        domain = settings.ALLOWED_HOSTS[0].split(".", 1)[1]
        cert_path = f"/etc/letsencrypt/live/{domain}"
    else:
        cert_path = "/opt/tactical/certs"

    config = {
        "tls": {
            "cert_file": f"{cert_path}/fullchain.pem",
            "key_file": f"{cert_path}/privkey.pem",
        },
        "authorization": {"users": users},
        "max_payload": 2048576005,
    }

    conf = os.path.join(settings.BASE_DIR, "nats-rmm.conf")
    with open(conf, "w") as f:
        json.dump(config, f)

    if not settings.DOCKER_BUILD:
        subprocess.run(
            ["/usr/local/bin/nats-server", "-signal", "reload"], capture_output=True
        )
