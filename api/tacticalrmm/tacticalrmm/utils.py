import json
import os
import string
import subprocess
import tempfile
import time
import urllib.parse
from typing import Optional, Union

import pytz
import requests
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import FileResponse
from knox.auth import TokenAuthentication
from loguru import logger
from rest_framework import status
from rest_framework.response import Response

from agents.models import Agent
from core.models import CodeSignToken

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


def generate_winagent_exe(
    client: int,
    site: int,
    agent_type: str,
    rdp: int,
    ping: int,
    power: int,
    arch: str,
    token: str,
    api: str,
    file_name: str,
) -> Union[Response, FileResponse]:

    from agents.utils import get_exegen_url

    inno = (
        f"winagent-v{settings.LATEST_AGENT_VER}.exe"
        if arch == "64"
        else f"winagent-v{settings.LATEST_AGENT_VER}-x86.exe"
    )

    try:
        codetoken = CodeSignToken.objects.first().token
        base_url = get_exegen_url() + "/api/v1/winagents/?"
        params = {
            "version": settings.LATEST_AGENT_VER,
            "arch": arch,
            "token": codetoken,
        }
        dl_url = base_url + urllib.parse.urlencode(params)
    except:
        codetoken = ""
        dl_url = settings.DL_64 if arch == "64" else settings.DL_32

    data = {
        "client": client,
        "site": site,
        "agenttype": agent_type,
        "rdp": str(rdp),
        "ping": str(ping),
        "power": str(power),
        "goarch": "amd64" if arch == "64" else "386",
        "token": token,
        "inno": inno,
        "url": dl_url,
        "api": api,
        "codesigntoken": codetoken,
    }
    headers = {"Content-type": "application/json"}

    errors = []
    with tempfile.NamedTemporaryFile() as fp:
        for url in settings.EXE_GEN_URLS:
            try:
                r = requests.post(
                    f"{url}/api/v1/exe",
                    json=data,
                    headers=headers,
                    stream=True,
                    timeout=900,
                )
            except Exception as e:
                errors.append(str(e))
            else:
                errors = []
                break

        if errors:
            logger.error(errors)
            return notify_error(
                "Something went wrong. Check debug error log for exact error message"
            )

        with open(fp.name, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):  # type: ignore
                if chunk:
                    f.write(chunk)
        del r
        return FileResponse(open(fp.name, "rb"), as_attachment=True, filename=file_name)


def get_default_timezone():
    from core.models import CoreSettings

    return pytz.timezone(CoreSettings.objects.first().default_time_zone)


def get_bit_days(days: list[str]) -> int:
    bit_days = 0
    for day in days:
        bit_days |= WEEK_DAYS.get(day)  # type: ignore
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


@database_sync_to_async
def get_user(access_token):
    try:
        auth = TokenAuthentication()
        token = access_token.decode().split("access_token=")[1]
        user = auth.authenticate_credentials(token.encode())
    except Exception:
        return AnonymousUser()
    else:
        return user[0]


class KnoxAuthMiddlewareInstance:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope["user"] = await get_user(scope["query_string"])

        return await self.app(scope, receive, send)


KnoxAuthMiddlewareStack = lambda inner: KnoxAuthMiddlewareInstance(
    AuthMiddlewareStack(inner)
)


def run_nats_api_cmd(mode: str, ids: list[str], timeout: int = 30) -> None:
    config = {
        "key": settings.SECRET_KEY,
        "natsurl": f"tls://{settings.ALLOWED_HOSTS[0]}:4222",
        "agents": ids,
    }
    with tempfile.NamedTemporaryFile() as fp:
        with open(fp.name, "w") as f:
            json.dump(config, f)

        cmd = ["/usr/local/bin/nats-api", "-c", fp.name, "-m", mode]
        try:
            subprocess.run(cmd, capture_output=True, timeout=timeout)
        except Exception as e:
            logger.error(e)


def get_latest_trmm_ver() -> str:
    url = "https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/api/tacticalrmm/tacticalrmm/settings.py"
    try:
        r = requests.get(url, timeout=5)
    except:
        return "error"

    try:
        for line in r.text.splitlines():
            if "TRMM_VERSION" in line:
                return line.split(" ")[2].strip('"')
    except Exception as e:
        logger.error(e)

    return "error"


def replace_db_values(
    string: str, agent: Agent = None, shell: str = None, quotes=True
) -> Union[str, None]:
    from core.models import CustomField, GlobalKVStore

    # split by period if exists. First should be model and second should be property i.e {{client.name}}
    temp = string.split(".")

    # check for model and property
    if len(temp) < 2:
        # ignore arg since it is invalid
        return None

    # value is in the global keystore and replace value
    if temp[0] == "global":
        if GlobalKVStore.objects.filter(name=temp[1]).exists():
            value = GlobalKVStore.objects.get(name=temp[1]).value

            return f"'{value}'" if quotes else value
        else:
            logger.error(
                f"Couldn't lookup value for: {string}. Make sure it exists in CoreSettings > Key Store"
            )
            return None

    if not agent:
        # agent must be set if not global property
        return f"There was an error finding the agent: {agent}"

    if temp[0] == "client":
        model = "client"
        obj = agent.client
    elif temp[0] == "site":
        model = "site"
        obj = agent.site
    elif temp[0] == "agent":
        model = "agent"
        obj = agent
    else:
        # ignore arg since it is invalid
        logger.error(
            f"Not enough information to find value for: {string}. Only agent, site, client, and global are supported."
        )
        return None

    if hasattr(obj, temp[1]):
        value = f"'{getattr(obj, temp[1])}'" if quotes else getattr(obj, temp[1])

    elif CustomField.objects.filter(model=model, name=temp[1]).exists():

        field = CustomField.objects.get(model=model, name=temp[1])
        model_fields = getattr(field, f"{model}_fields")
        value = None
        if model_fields.filter(**{model: obj}).exists():
            if field.type != "checkbox" and model_fields.get(**{model: obj}).value:
                value = model_fields.get(**{model: obj}).value
            elif field.type == "checkbox":
                value = model_fields.get(**{model: obj}).value

        # need explicit None check since a false boolean value will pass default value
        if value == None and field.default_value != None:
            value = field.default_value

        # check if value exists and if not use default
        if value and field.type == "multiple":
            value = (
                f"'{format_shell_array(value)}'"
                if quotes
                else format_shell_array(value)
            )
        elif value != None and field.type == "checkbox":
            value = format_shell_bool(value, shell)
        else:
            value = f"'{value}'" if quotes else value

    else:
        # ignore arg since property is invalid
        logger.error(
            f"Couldn't find property on supplied variable: {string}. Make sure it exists as a custom field or a valid agent property"
        )
        return None

    # log any unhashable type errors
    if value != None:
        return value  # type: ignore
    else:
        logger.error(
            f"Couldn't lookup value for: {string}. Make sure it exists as a custom field or a valid agent property"
        )
        return None


def format_shell_array(value: list) -> str:
    temp_string = ""
    for item in value:
        temp_string += item + ","
    return f"{temp_string.strip(',')}"


def format_shell_bool(value: bool, shell: Optional[str]) -> str:
    if shell == "powershell":
        return "$True" if value else "$False"
    else:
        return "1" if value else "0"
