import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from functools import wraps
from typing import List, Optional, Union
from zoneinfo import ZoneInfo

import requests
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.db import connection
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
    get_nats_internal_protocol,
    get_nats_ports,
    notify_error,
)


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
    nats_std_port, nats_ws_port = get_nats_ports()

    config = {
        "authorization": {"users": users},
        "max_payload": 67108864,
        "port": nats_std_port,  # internal only
        "websocket": {
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


def replace_db_values(
    string: str, instance=None, shell: str = None, quotes=True  # type:ignore
) -> Union[str, None]:
    from clients.models import Client, Site
    from core.models import CustomField, GlobalKVStore

    # split by period if exists. First should be model and second should be property i.e {{client.name}}
    temp = string.split(".")

    # check for model and property
    if len(temp) < 2:
        # ignore arg since it is invalid
        return ""

    # value is in the global keystore and replace value
    if temp[0] == "global":
        if GlobalKVStore.objects.filter(name=temp[1]).exists():
            value = GlobalKVStore.objects.get(name=temp[1]).value

            return f"'{value}'" if quotes else value
        else:
            DebugLog.error(
                log_type=DebugLogType.SCRIPTING,
                message=f"Couldn't lookup value for: {string}. Make sure it exists in CoreSettings > Key Store",  # type:ignore
            )
            return ""

    if not instance:
        # instance must be set if not global property
        return ""

    if temp[0] == "client":
        model = "client"
        if isinstance(instance, Client):
            obj = instance
        elif hasattr(instance, "client"):
            obj = instance.client
        else:
            obj = None
    elif temp[0] == "site":
        model = "site"
        if isinstance(instance, Site):
            obj = instance
        elif hasattr(instance, "site"):
            obj = instance.site
        else:
            obj = None
    elif temp[0] == "agent":
        model = "agent"
        if isinstance(instance, Agent):
            obj = instance
        else:
            obj = None
    else:
        # ignore arg since it is invalid
        DebugLog.error(
            log_type=DebugLogType.SCRIPTING,
            message=f"{instance} Not enough information to find value for: {string}. Only agent, site, client, and global are supported.",
        )
        return ""

    if not obj:
        return ""

    # check if attr exists and isn't a function
    if hasattr(obj, temp[1]) and not callable(getattr(obj, temp[1])):
        temp1 = getattr(obj, temp[1])
        if shell == ScriptShell.POWERSHELL and isinstance(temp1, str) and "'" in temp1:
            temp1 = temp1.replace("'", "''")

        value = f"'{temp1}'" if quotes else temp1

    elif CustomField.objects.filter(model=model, name=temp[1]).exists():
        field = CustomField.objects.get(model=model, name=temp[1])
        model_fields = getattr(field, f"{model}_fields")
        value = None
        if model_fields.filter(**{model: obj}).exists():
            if (
                field.type != CustomFieldType.CHECKBOX
                and model_fields.get(**{model: obj}).value
            ):
                value = model_fields.get(**{model: obj}).value
            elif field.type == CustomFieldType.CHECKBOX:
                value = model_fields.get(**{model: obj}).value

        # need explicit None check since a false boolean value will pass default value
        if value is None and field.default_value is not None:
            value = field.default_value

        # check if value exists and if not use default
        if value and field.type == CustomFieldType.MULTIPLE:
            value = (
                f"'{format_shell_array(value)}'"
                if quotes
                else format_shell_array(value)
            )
        elif value is not None and field.type == CustomFieldType.CHECKBOX:
            value = format_shell_bool(value, shell)
        else:
            if (
                shell == ScriptShell.POWERSHELL
                and isinstance(value, str)
                and "'" in value
            ):
                value = value.replace("'", "''")

            value = f"'{value}'" if quotes else value

    else:
        # ignore arg since property is invalid
        DebugLog.error(
            log_type=DebugLogType.SCRIPTING,
            message=f"{instance} Couldn't find property on supplied variable: {string}. Make sure it exists as a custom field or a valid agent property",
        )
        return ""

    # log any unhashable type errors
    if value is not None:
        return value
    else:
        DebugLog.error(
            log_type=DebugLogType.SCRIPTING,
            message=f" {instance}({instance.pk}) Couldn't lookup value for: {string}. Make sure it exists as a custom field or a valid agent property",
        )
        return ""


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


# https://stackoverflow.com/a/57794016
class DjangoConnectionThreadPoolExecutor(ThreadPoolExecutor):
    """
    When a function is passed into the ThreadPoolExecutor via either submit() or map(),
    this will wrap the function, and make sure that close_django_db_connection() is called
    inside the thread when it's finished so Django doesn't leak DB connections.

    Since map() calls submit(), only submit() needs to be overwritten.
    """

    def close_django_db_connection(self):
        connection.close()

    def generate_thread_closing_wrapper(self, fn):
        @wraps(fn)
        def new_func(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            finally:
                self.close_django_db_connection()

        return new_func

    def submit(*args, **kwargs):
        if len(args) >= 2:
            self, fn, *args = args
            fn = self.generate_thread_closing_wrapper(fn=fn)
        elif not args:
            raise TypeError(
                "descriptor 'submit' of 'ThreadPoolExecutor' object "
                "needs an argument"
            )
        elif "fn" in kwargs:
            fn = self.generate_thread_closing_wrapper(fn=kwargs.pop("fn"))
            self, *args = args

        return super(self.__class__, self).submit(fn, *args, **kwargs)


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
