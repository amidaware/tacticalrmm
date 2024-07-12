import json
import os
import subprocess
import tempfile
import time
import re
from contextlib import contextmanager
from typing import TYPE_CHECKING, List, Literal, Optional, Union
from zoneinfo import ZoneInfo

import requests
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.http import FileResponse
from knox.auth import TokenAuthentication
from rest_framework.response import Response

from agents.models import Agent
from core.utils import get_core_settings, token_is_valid
from logs.models import DebugLog
from tacticalrmm.constants import (
    MONTH_DAYS,
    MONTHS,
    REDIS_LOCK_EXPIRE,
    WEEK_DAYS,
    WEEKS,
    AgentPlat,
    CustomFieldType,
    DebugLogType,
    ScriptShell,
)
from tacticalrmm.helpers import (
    get_certs,
    get_nats_hosts,
    get_nats_internal_protocol,
    get_nats_ports,
    notify_error,
)

if TYPE_CHECKING:
    from clients.models import Client, Site
    from alerts.models import Alert


def generate_winagent_exe(
    *,
    client: int,
    site: int,
    agent_type: str,
    rdp: int,
    ping: int,
    power: int,
    goarch: str,
    token: str,
    api: str,
    file_name: str,
) -> Union[Response, FileResponse]:
    from agents.utils import get_agent_url

    inno = (
        f"tacticalagent-v{settings.LATEST_AGENT_VER}-{AgentPlat.WINDOWS}-{goarch}.exe"
    )

    codetoken, _ = token_is_valid()

    dl_url = get_agent_url(goarch=goarch, plat=AgentPlat.WINDOWS, token=codetoken)

    data = {
        "client": client,
        "site": site,
        "agenttype": agent_type,
        "rdp": str(rdp),
        "ping": str(ping),
        "power": str(power),
        "goarch": goarch,
        "token": token,
        "inno": inno,
        "url": dl_url,
        "api": api,
        "codesigntoken": codetoken,
    }
    headers = {"Content-type": "application/json"}

    with tempfile.NamedTemporaryFile() as fp:
        try:
            r = requests.post(
                settings.EXE_GEN_URL,
                json=data,
                headers=headers,
                stream=True,
                timeout=900,
            )
        except Exception as e:
            DebugLog.error(message=str(e))
            return notify_error(
                "Something went wrong. Check debug error log for exact error message"
            )

        with open(fp.name, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        del r
        return FileResponse(open(fp.name, "rb"), as_attachment=True, filename=file_name)


def get_default_timezone():
    return ZoneInfo(get_core_settings().default_time_zone)


def get_bit_days(days: list[str]) -> int:
    bit_days = 0
    for day in days:
        bit_days |= WEEK_DAYS.get(day, 0)
    return bit_days


def bitdays_to_string(day: int) -> str:
    ret: List[str] = []
    if day == 127:
        return "Every day"

    for key, value in WEEK_DAYS.items():
        if day & value:
            ret.append(key)
    return ", ".join(ret)


def bitmonths_to_string(month: int) -> str:
    ret: List[str] = []
    if month == 4095:
        return "Every month"

    for key, value in MONTHS.items():
        if month & value:
            ret.append(key)
    return ", ".join(ret)


def bitweeks_to_string(week: int) -> str:
    ret: List[str] = []
    if week == 31:
        return "Every week"

    for key, value in WEEKS.items():
        if week & value:
            ret.append(key)
    return ", ".join(ret)


def bitmonthdays_to_string(day: int) -> str:
    ret: List[str] = []

    if day == MONTH_DAYS["Last Day"]:
        return "Last day"
    elif day in (2147483647, 4294967295):
        return "Every day"

    for key, value in MONTH_DAYS.items():
        if day & value:
            ret.append(key)
    return ", ".join(ret)


def convert_to_iso_duration(string: str) -> str:
    tmp = string.upper()
    if "D" in tmp:
        return f"P{tmp.replace('D', 'DT')}"

    return f"PT{tmp}"


def reload_nats() -> None:
    users = [
        {
            "user": "tacticalrmm",
            "password": settings.SECRET_KEY,
            "permissions": {"publish": ">", "subscribe": ">"},
        }
    ]
    agents = Agent.objects.prefetch_related("user").only(
        "pk", "agent_id"
    )  # type:ignore
    for agent in agents:
        try:
            users.append(
                {
                    "user": agent.agent_id,
                    "password": agent.user.auth_token.key,
                    "permissions": {
                        "publish": {"allow": agent.agent_id},
                        "subscribe": {"allow": agent.agent_id},
                        "allow_responses": {
                            "expires": getattr(
                                settings, "NATS_ALLOW_RESPONSE_EXPIRATION", "1435m"
                            )
                        },
                    },
                }
            )
        except:
            DebugLog.critical(
                agent=agent,
                log_type=DebugLogType.AGENT_ISSUES,
                message=f"{agent.hostname} does not have a user account, NATS will not work",
            )

    cert_file, key_file = get_certs()
    nats_std_host, nats_ws_host, _ = get_nats_hosts()
    nats_std_port, nats_ws_port = get_nats_ports()

    config = {
        "authorization": {"users": users},
        "max_payload": 67108864,
        "host": nats_std_host,
        "port": nats_std_port,  # internal only
        "websocket": {
            "host": nats_ws_host,
            "port": nats_ws_port,
            "no_tls": True,  # TLS is handled by nginx, so not needed here
        },
    }

    if get_nats_internal_protocol() == "tls":
        config["tls"] = {
            "cert_file": cert_file,
            "key_file": key_file,
        }

    if "NATS_HTTP_PORT" in os.environ:
        config["http_port"] = int(os.getenv("NATS_HTTP_PORT"))  # type: ignore
    elif hasattr(settings, "NATS_HTTP_PORT"):
        config["http_port"] = settings.NATS_HTTP_PORT  # type: ignore

    if "NATS_WS_COMPRESSION" in os.environ or hasattr(settings, "NATS_WS_COMPRESSION"):
        config["websocket"]["compression"] = True

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


KnoxAuthMiddlewareStack = lambda inner: KnoxAuthMiddlewareInstance(  # noqa
    AuthMiddlewareStack(inner)
)


def get_latest_trmm_ver() -> str:
    url = "https://raw.githubusercontent.com/amidaware/tacticalrmm/master/api/tacticalrmm/tacticalrmm/settings.py"
    try:
        r = requests.get(url, timeout=5)
    except:
        return "error"

    try:
        for line in r.text.splitlines():
            if "TRMM_VERSION" in line:
                return line.split(" ")[2].strip('"')
    except Exception as e:
        DebugLog.error(message=str(e))

    return "error"


# regex for db data replacement
# will return 3 groups of matches in a tuple when uses with re.findall
# i.e. - {{client.name}}, client, name
RE_DB_VALUE = re.compile(
    r"(\{\{\s*(client|site|agent|global|alert)(?:\.([\w\-\s\.]+))+\s*\}\})"
)


# Receives something like {{ client.name }} and a Model instance of Client, Site, or Agent. If an
# agent instance is passed it will resolve the value of agent.client.name and return the agent's client name.
#
# You can query custom fields by using their name. {{ site.Custom Field Name }}
#
# This will recursively lookup values for relations. {{ client.site.id }}
#
# You can also use {{ global.value }} without an obj instance to use the global key store
def get_db_value(
    *, string: str, instance: Optional[Union["Agent", "Client", "Site", "Alert"]] = None
) -> Union[str, List[str], Literal[True], Literal[False], None]:
    from core.models import CustomField, GlobalKVStore

    # get properties into an array
    props = string.strip().split(".")

    # value is in the global keystore and replace value
    if props[0] == "global" and len(props) == 2:
        try:
            return GlobalKVStore.objects.get(name=props[1]).value
        except GlobalKVStore.DoesNotExist:
            DebugLog.error(
                log_type=DebugLogType.SCRIPTING,
                message=f"Couldn't lookup value for: {string}. Make sure it exists in CoreSettings > Key Store",
            )
            return None

    if not instance:
        # instance must be set if not global property
        return None

    # custom field lookup
    try:
        # looking up custom field directly on this instance
        if len(props) == 2:
            field = CustomField.objects.get(model=props[0], name=props[1])
            model_fields = getattr(field, f"{props[0]}_fields")

            try:
                # resolve the correct model id
                if props[0] != instance.__class__.__name__.lower():
                    value = model_fields.get(
                        **{props[0]: getattr(instance, props[0])}
                    ).value
                else:
                    value = model_fields.get(**{f"{props[0]}_id": instance.id}).value

                if field.type != CustomFieldType.CHECKBOX:
                    if value:
                        return value
                    else:
                        return field.default_value
                else:
                    return bool(value)
            except:
                return (
                    field.default_value
                    if field.type != CustomFieldType.CHECKBOX
                    else bool(field.default_value)
                )
    except CustomField.DoesNotExist:
        pass

    # if the instance is the same as the first prop. We remove it.
    if props[0] == instance.__class__.__name__.lower():
        del props[0]

    instance_value = instance

    # look through all properties and return the value
    for prop in props:
        if hasattr(instance_value, prop):
            value = getattr(instance_value, prop)
            if callable(value):
                return None
            instance_value = value

        if not instance_value:
            return None

    return instance_value


def replace_arg_db_values(
    string: str, instance=None, shell: str = None, quotes=True  # type:ignore
) -> Union[str, None]:
    # resolve the value
    value = get_db_value(string=string, instance=instance)

    # check for model and property
    if value is None:
        DebugLog.error(
            log_type=DebugLogType.SCRIPTING,
            message=f"Couldn't lookup value for: {string}. Make sure it exists",
        )
        return ""

    # format args for str
    if isinstance(value, str):
        if shell == ScriptShell.POWERSHELL and "'" in value:
            value = value.replace("'", "''")

        return f"'{value}'" if quotes else value

    # format args for list
    elif isinstance(value, list):
        return f"'{format_shell_array(value)}'" if quotes else format_shell_array(value)

    # format args for bool
    elif value is True or value is False:
        return format_shell_bool(value, shell)

    elif isinstance(value, dict):
        return json.dumps(value)

    # return str for everything else
    try:
        ret = str(value)
    except Exception:
        ret = ""

    return ret


def format_shell_array(value: list[str]) -> str:
    temp_string = ""
    for item in value:
        temp_string += item + ","
    return f"{temp_string.strip(',')}"


def format_shell_bool(value: bool, shell: Optional[str]) -> str:
    if shell == ScriptShell.POWERSHELL:
        return "$True" if value else "$False"

    return "1" if value else "0"


# https://docs.celeryq.dev/en/latest/tutorials/task-cookbook.html#cookbook-task-serial
@contextmanager
def redis_lock(lock_id, oid):
    timeout_at = time.monotonic() + REDIS_LOCK_EXPIRE - 3
    status = cache.add(lock_id, oid, REDIS_LOCK_EXPIRE)
    try:
        yield status
    finally:
        if time.monotonic() < timeout_at and status:
            cache.delete(lock_id)


def runcmd_placeholder_text() -> dict[str, str]:
    ret = {
        "cmd": getattr(
            settings,
            "CMD_PLACEHOLDER_TEXT",
            "rmdir /S /Q C:\\Windows\\System32",
        ),
        "powershell": getattr(
            settings,
            "POWERSHELL_PLACEHOLDER_TEXT",
            "Remove-Item -Recurse -Force C:\\Windows\\System32",
        ),
        "shell": getattr(
            settings, "SHELL_PLACEHOLDER_TEXT", "rm -rf --no-preserve-root /"
        ),
    }
    return ret
