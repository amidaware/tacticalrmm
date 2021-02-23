import json
import os
import string
import subprocess
import time
from typing import Union

import pytz
from django.conf import settings
from django.http import HttpResponse
from loguru import logger
from rest_framework import status
from rest_framework.response import Response

from agents.models import Agent

logger.configure(**settings.LOG_CONFIG)

notify_error = lambda msg: Response(msg, status=status.HTTP_400_BAD_REQUEST)

SoftwareList = list[dict[str, str]]

WEEK_DAYS = {
    "Sunday": 0x1,
    "Monday": 0x2,
    "Tuesday": 0x4,
    "Wednesday": 0x8,
    "Thursday": 0x10,
    "Friday": 0x20,
    "Saturday": 0x40,
}


def generate_installer_exe(
    file_name: str,
    goarch: str,
    inno: str,
    api: str,
    client_id: int,
    site_id: int,
    atype: str,
    rdp: int,
    ping: int,
    power: int,
    download_url: str,
    token: str,
) -> Union[Response, HttpResponse]:

    go_bin = "/usr/local/rmmgo/go/bin/go"
    if not os.path.exists(go_bin):
        return Response("nogolang", status=status.HTTP_409_CONFLICT)

    exe = os.path.join(settings.EXE_DIR, file_name)
    if os.path.exists(exe):
        try:
            os.remove(exe)
        except Exception as e:
            logger.error(str(e))

    cmd = [
        "env",
        "CGO_ENABLED=0",
        "GOOS=windows",
        f"GOARCH={goarch}",
        go_bin,
        "build",
        f"-ldflags=\"-s -w -X 'main.Inno={inno}'",
        f"-X 'main.Api={api}'",
        f"-X 'main.Client={client_id}'",
        f"-X 'main.Site={site_id}'",
        f"-X 'main.Atype={atype}'",
        f"-X 'main.Rdp={rdp}'",
        f"-X 'main.Ping={ping}'",
        f"-X 'main.Power={power}'",
        f"-X 'main.DownloadUrl={download_url}'",
        f"-X 'main.Token={token}'\"",
        "-o",
        exe,
    ]

    build_error = False
    gen_error = False

    gen = [
        "env",
        "GOOS=windows",
        "CGO_ENABLED=0",
        f"GOARCH={goarch}",
        go_bin,
        "generate",
    ]

    try:
        r1 = subprocess.run(
            " ".join(gen),
            capture_output=True,
            shell=True,
            cwd=os.path.join(settings.BASE_DIR, "core/goinstaller"),
        )
    except Exception as e:
        gen_error = True
        logger.error(str(e))
        return Response("genfailed", status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    if r1.returncode != 0:
        gen_error = True
        if r1.stdout:
            logger.error(r1.stdout.decode("utf-8", errors="ignore"))

        if r1.stderr:
            logger.error(r1.stderr.decode("utf-8", errors="ignore"))

        logger.error(f"Go build failed with return code {r1.returncode}")

    if gen_error:
        return Response("genfailed", status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    try:
        r = subprocess.run(
            " ".join(cmd),
            capture_output=True,
            shell=True,
            cwd=os.path.join(settings.BASE_DIR, "core/goinstaller"),
        )
    except Exception as e:
        build_error = True
        logger.error(str(e))
        return Response("buildfailed", status=status.HTTP_412_PRECONDITION_FAILED)

    if r.returncode != 0:
        build_error = True
        if r.stdout:
            logger.error(r.stdout.decode("utf-8", errors="ignore"))

        if r.stderr:
            logger.error(r.stderr.decode("utf-8", errors="ignore"))

        logger.error(f"Go build failed with return code {r.returncode}")

    if build_error:
        return Response("buildfailed", status=status.HTTP_412_PRECONDITION_FAILED)

    if settings.DEBUG:
        with open(exe, "rb") as f:
            response = HttpResponse(
                f.read(),
                content_type="application/vnd.microsoft.portable-executable",
            )
            response["Content-Disposition"] = f"inline; filename={file_name}"
            return response
    else:
        response = HttpResponse()
        response["Content-Disposition"] = f"attachment; filename={file_name}"
        response["X-Accel-Redirect"] = f"/private/exe/{file_name}"
        return response


def get_default_timezone():
    from core.models import CoreSettings

    return pytz.timezone(CoreSettings.objects.first().default_time_zone)


def get_bit_days(days: list[str]) -> int:
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

    domain = settings.ALLOWED_HOSTS[0].split(".", 1)[1]
    if hasattr(settings, "CERT_FILE") and hasattr(settings, "KEY_FILE"):
        if os.path.exists(settings.CERT_FILE) and os.path.exists(settings.KEY_FILE):
            cert_file = settings.CERT_FILE
            key_file = settings.KEY_FILE
        else:
            cert_file = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
            key_file = f"/etc/letsencrypt/live/{domain}/privkey.pem"
    else:
        cert_file = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        key_file = f"/etc/letsencrypt/live/{domain}/privkey.pem"

    config = {
        "tls": {
            "cert_file": cert_file,
            "key_file": key_file,
        },
        "authorization": {"users": users},
        "max_payload": 2048576005,
    }

    conf = os.path.join(settings.BASE_DIR, "nats-rmm.conf")
    with open(conf, "w") as f:
        json.dump(config, f)

    if not settings.DOCKER_BUILD:
        time.sleep(0.5)
        subprocess.run(
            ["/usr/local/bin/nats-server", "-signal", "reload"], capture_output=True
        )
