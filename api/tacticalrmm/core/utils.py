import json
import tempfile
from base64 import b64encode
from meshctrl.utils import get_auth_token

from typing import cast, TYPE_CHECKING
import requests
import websockets
from django.core.cache import cache
from django.conf import settings
from django.http import FileResponse

if TYPE_CHECKING:
    from core.models import CoreSettings


class CoreSettingsNotFound(Exception):
    pass


def get_core_settings() -> "CoreSettings":
    from core.models import CoreSettings, CORESETTINGS_CACHE_KEY

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
    token = get_auth_token(core.mesh_username, core.mesh_token)

    if settings.DOCKER_BUILD:
        uri = f"{settings.MESH_WS_URL}/control.ashx?auth={token}"
    else:
        site = core.mesh_site.replace("https", "wss")
        uri = f"{site}/control.ashx?auth={token}"

    return uri


async def get_mesh_device_id(uri: str, device_group: str) -> None:
    async with websockets.connect(uri) as ws:
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
        r = requests.get(dl_url, stream=True, timeout=15)
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
