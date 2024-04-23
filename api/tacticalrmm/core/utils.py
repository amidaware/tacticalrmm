import json
import os
import subprocess
import tempfile
import time
import urllib.parse
from base64 import b64encode
from contextlib import suppress
from requests.utils import requote_uri
from typing import TYPE_CHECKING, List, Optional, cast, Tuple

import requests
import websockets
from django.conf import settings
from django.core.cache import cache
from django.http import FileResponse
from django.utils import timezone as djangotime
from django.apps import apps
from meshctrl.utils import get_auth_token

from tacticalrmm.constants import (
    AGENT_TBL_PEND_ACTION_CNT_CACHE_PREFIX,
    CORESETTINGS_CACHE_KEY,
    ROLE_CACHE_PREFIX,
    TRMM_WS_MAX_SIZE,
    AgentPlat,
    MeshAgentIdent,
)

if TYPE_CHECKING:
    from core.models import CoreSettings


class CoreSettingsNotFound(Exception):
    pass


def clear_entire_cache() -> None:
    cache.delete_many_pattern(f"{ROLE_CACHE_PREFIX}*")
    cache.delete_many_pattern(f"{AGENT_TBL_PEND_ACTION_CNT_CACHE_PREFIX}*")
    cache.delete(CORESETTINGS_CACHE_KEY)
    cache.delete_many_pattern("site_*")
    cache.delete_many_pattern("agent_*")


def token_is_valid() -> tuple[str, bool]:
    """
    Return type: token: str, is_valid: bool. Token wil be an empty string is not valid.
    """
    from core.models import CodeSignToken

    t: "Optional[CodeSignToken]" = CodeSignToken.objects.first()
    if not t:
        return "", False

    if not t.token:
        return "", False

    if t.is_valid:
        return t.token, True

    return "", False


def token_is_expired() -> bool:
    from core.models import CodeSignToken

    t: Optional["CodeSignToken"] = CodeSignToken.objects.first()
    if not t or not t.token:
        return False

    return t.is_expired


def get_core_settings() -> "CoreSettings":
    from core.models import CORESETTINGS_CACHE_KEY, CoreSettings

    coresettings = cache.get(CORESETTINGS_CACHE_KEY)

    if coresettings and isinstance(coresettings, CoreSettings):
        return coresettings
    else:
        coresettings = CoreSettings.objects.first()
        if not coresettings:
            raise CoreSettingsNotFound("CoreSettings not found.")

        cache.set(CORESETTINGS_CACHE_KEY, coresettings, 600)
        return cast(CoreSettings, coresettings)


def get_mesh_ws_url() -> str:
    core = get_core_settings()
    token = get_auth_token(core.mesh_api_superuser, core.mesh_token)

    if settings.DOCKER_BUILD:
        uri = f"{settings.MESH_WS_URL}/control.ashx?auth={token}"
    else:
        if getattr(settings, "USE_EXTERNAL_MESH", False):
            site = core.mesh_site.replace("https", "wss")
            uri = f"{site}/control.ashx?auth={token}"
        else:
            mesh_port = getattr(settings, "MESH_PORT", 4430)
            uri = f"ws://127.0.0.1:{mesh_port}/control.ashx?auth={token}"

    return uri


async def get_mesh_device_id(uri: str, device_group: str) -> None:
    async with websockets.connect(uri, max_size=TRMM_WS_MAX_SIZE) as ws:
        payload = {"action": "meshes", "responseid": "meshctrl"}
        await ws.send(json.dumps(payload))

        async for message in ws:
            r = json.loads(message)
            if r["action"] == "meshes":
                return list(filter(lambda x: x["name"] == device_group, r["meshes"]))[
                    0
                ]["_id"].split("mesh//")[1]


def download_mesh_agent(dl_url: str) -> FileResponse:
    with tempfile.NamedTemporaryFile(prefix="mesh-", dir=settings.EXE_DIR) as fp:
        r = requests.get(dl_url, stream=True, timeout=15, verify=False)
        with open(fp.name, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        del r

        return FileResponse(open(fp.name, "rb"), as_attachment=True, filename=fp.name)


def _b64_to_hex(h: str) -> str:
    return b64encode(bytes.fromhex(h)).decode().replace(r"/", "$").replace(r"+", "@")


async def send_command_with_mesh(
    cmd: str, uri: str, mesh_node_id: str, shell: int, run_as_user: int
) -> None:
    node_id = _b64_to_hex(mesh_node_id)
    async with websockets.connect(uri) as ws:
        await ws.send(
            json.dumps(
                {
                    "action": "runcommands",
                    "cmds": cmd,
                    "nodeids": [f"node//{node_id}"],
                    "runAsUser": run_as_user,
                    "type": shell,
                    "responseid": "trmm",
                }
            )
        )


async def wake_on_lan(*, uri: str, mesh_node_id: str) -> None:
    node_id = _b64_to_hex(mesh_node_id)
    async with websockets.connect(uri) as ws:
        await ws.send(
            json.dumps(
                {
                    "action": "wakedevices",
                    "nodeids": [f"node//{node_id}"],
                    "responseid": "trmm",
                }
            )
        )


async def remove_mesh_agent(uri: str, mesh_node_id: str) -> None:
    node_id = _b64_to_hex(mesh_node_id)
    async with websockets.connect(uri) as ws:
        await ws.send(
            json.dumps(
                {
                    "action": "removedevices",
                    "nodeids": [f"node//{node_id}"],
                    "responseid": "trmm",
                }
            )
        )


def sysd_svc_is_running(svc: str) -> bool:
    cmd = ["systemctl", "is-active", "--quiet", svc]
    r = subprocess.run(cmd, capture_output=True)
    return not r.returncode


def get_meshagent_url(
    *, ident: "MeshAgentIdent", plat: str, mesh_site: str, mesh_device_id: str
) -> str:
    if settings.DOCKER_BUILD:
        base = settings.MESH_WS_URL.replace("ws://", "http://")
    elif getattr(settings, "USE_EXTERNAL_MESH", False):
        base = mesh_site
    else:
        mesh_port = getattr(settings, "MESH_PORT", 4430)
        base = f"http://127.0.0.1:{mesh_port}"

    if plat == AgentPlat.WINDOWS:
        params = {
            "id": ident,
            "meshid": mesh_device_id,
            "installflags": 0,
        }
    else:
        params = {
            "id": mesh_device_id,
            "installflags": 2,
            "meshinstall": ident,
        }

    return base + "/meshagents?" + urllib.parse.urlencode(params)


def make_alpha_numeric(s: str):
    return "".join(filter(str.isalnum, s))


def find_and_replace_db_values_str(*, text: str, instance):
    import re
    from tacticalrmm.utils import RE_DB_VALUE, get_db_value

    if not instance:
        return text
    
    return_string = text

    for string, model, prop in re.findall(RE_DB_VALUE, text):
        value = get_db_value(string=f"{model}.{prop}", instance=instance)
        return_string = return_string.replace(string, str(value))
    return return_string


def _run_url_rest_action(*, url: str, method, body: str, headers: str, instance=None):
    # replace url
    new_url = find_and_replace_db_values_str(text=url, instance=instance)
    new_body = find_and_replace_db_values_str(
        text=body, instance=instance
    )
    new_headers = find_and_replace_db_values_str(
        text=headers, instance=instance
    )
    new_url = requote_uri(new_url)
    new_body = json.loads(new_body)
    new_headers = json.loads(new_headers)

    if method in ["get", "delete"]:
        return getattr(requests, method)(new_url, headers=new_headers)

    return getattr(requests, method)(new_url, data=json.dumps(new_body), headers=new_headers)


def run_url_rest_action(*, action_id: int, instance=None) -> Tuple[str, int]:
    import core.models

    action = core.models.URLAction.objects.get(pk=action_id)
    method = action.rest_method
    url = action.pattern
    body = action.rest_body
    headers = action.rest_headers

    response = _run_url_rest_action(
        url=url, method=method, body=body, headers=headers, instance=instance
    )

    return (response.text, response.status_code)


lookup_apps = {
    "client": ("clients", "Client"),
    "site": ("clients", "Site"),
    "agent": ("agents", "Agent")
}

def run_test_url_rest_action(
    *,
    url: str,
    method,
    body: str,
    headers: str,
    instance_type: Optional[str],
    instance_id: Optional[int],
) -> Tuple[str, str, str]:
    lookup_instance = None
    if instance_type and instance_type in lookup_apps.keys() and instance_id:
        app, model = lookup_apps[instance_type]
        Model = apps.get_model(app, model)
        if instance_type == "agent":
            lookup_instance = Model.objects.get(agent_id=instance_id)
        else:
            lookup_instance = Model.objects.get(pk=instance_id)

    response = _run_url_rest_action(
        url=url, method=method, body=body, headers=headers, instance=lookup_instance
    )

    return (response.text, response.request.url, response.request.body)


def run_server_task(*, server_task_id: int):
    from autotasks.models import AutomatedTask, TaskResult
    from tacticalrmm.constants import TaskStatus

    task = AutomatedTask.objects.get(pk=server_task_id)
    output = ""
    total_execution_time = 0
    passing = True

    for action in task.actions:
        if action["type"] == "cmd":
            stdout, stderr, execution_time, retcode = run_server_command(
                command=action["command"], timeout=action["timeout"]
            )
            name = action["command"]
        else:
            stdout, stderr, execution_time, retcode = run_server_script(
                script_id=action["script"],
                args=action["script_args"],
                env_vars=action["env_vars"],
                timeout=action["timeout"],
            )
            name = action["name"]

        if retcode != 0:
            passing = False

        total_execution_time += execution_time
        output += f"-----------------------------\n{name}\n-----------------------------\n\nStandard Output: {stdout}\n\nStandard Error: {stderr}\n"
        output += f"Return Code: {retcode}\n"
        output += f"Execution Time: {execution_time}\n\n"

    try:
        task_result = TaskResult.objects.get(task=task, agent=None)
        task_result.retcode = 0 if passing else 1
        task_result.execution_time = total_execution_time
        task_result.stdout = output
        task_result.stderr = ""
        task_result.status = TaskStatus.PASSING if passing else TaskStatus.FAILING
        task_result.save()
    except TaskResult.DoesNotExist:
        TaskResult.objects.create(
            task=task,
            agent=None,
            retcode=0 if passing else 1,
            execution_time=total_execution_time,
            stdout=output,
            stderr="",
            status=TaskStatus.PASSING if passing else TaskStatus.FAILING,
            last_run=djangotime.now(),
        )

    return (output, total_execution_time)


def run_server_command(*, command: List[str], timeout: int):
    start_time = time.time()
    result = subprocess.run(
        command, capture_output=True, text=True, shell=True, timeout=timeout
    )
    execution_time = time.time() - start_time

    return (result.stdout, result.stderr, execution_time, result.returncode)


def run_server_script(
    *, script_id: int, args: List[str], env_vars: List[str], timeout: int
):
    from scripts.models import Script

    script = Script.objects.get(pk=script_id)

    parsed_args = script.parse_script_args(None, script.shell, args)

    parsed_env_vars = script.parse_script_env_vars(
        None, shell=script.shell, env_vars=env_vars
    )

    custom_env = os.environ.copy()
    for var in parsed_env_vars:
        var_split = var.split("=")
        custom_env[var_split[0]] = var_split[1]

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_script:
        tmp_script.write(script.script_body.replace("\r\n", "\n"))
        tmp_script_path = tmp_script.name

    os.chmod(tmp_script_path, 0o550)

    start_time = time.time()
    result = subprocess.run(
        [tmp_script_path] + parsed_args,
        capture_output=True,
        text=True,
        env=custom_env,
        timeout=timeout,
    )
    execution_time = time.time() - start_time

    with suppress(Exception):
        os.remove(tmp_script_path)

    return result.stdout, result.stderr, execution_time, result.returncode
