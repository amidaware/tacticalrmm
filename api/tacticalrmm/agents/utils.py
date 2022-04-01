import asyncio
import tempfile
import urllib.parse

from core.models import CodeSignToken
from core.utils import get_mesh_device_id, get_mesh_ws_url, get_core_settings
from django.conf import settings
from django.http import FileResponse

from tacticalrmm.constants import MeshAgentIdent


def get_agent_url(arch: str, plat: str) -> str:

    if plat == "windows":
        endpoint = "winagents"
        dl_url = settings.DL_32 if arch == "32" else settings.DL_64
    else:
        endpoint = "linuxagents"
        dl_url = ""

    token = CodeSignToken.objects.first()
    if not token:
        return dl_url

    if token.is_valid:
        base_url = settings.EXE_GEN_URL + f"/api/v1/{endpoint}/?"
        params = {
            "version": settings.LATEST_AGENT_VER,
            "arch": arch,
            "token": token.token,
        }
        dl_url = base_url + urllib.parse.urlencode(params)

    return dl_url


def generate_linux_install(
    client: str,
    site: str,
    agent_type: str,
    arch: str,
    token: str,
    api: str,
    download_url: str,
) -> FileResponse:

    match arch:
        case "amd64":
            arch_id = MeshAgentIdent.LINUX64
        case "386":
            arch_id = MeshAgentIdent.LINUX32
        case "arm64":
            arch_id = MeshAgentIdent.LINUX_ARM_64
        case "arm":
            arch_id = MeshAgentIdent.LINUX_ARM_HF
        case _:
            arch_id = "not_found"

    core = get_core_settings()

    uri = get_mesh_ws_url()
    mesh_id = asyncio.run(get_mesh_device_id(uri, core.mesh_device_group))
    mesh_dl = (
        f"{core.mesh_site}/meshagents?id={mesh_id}&installflags=0&meshinstall={arch_id}"
    )

    sh = settings.LINUX_AGENT_SCRIPT
    with open(sh, "r") as f:
        text = f.read()

    replace = {
        "agentDLChange": download_url,
        "meshDLChange": mesh_dl,
        "clientIDChange": client,
        "siteIDChange": site,
        "agentTypeChange": agent_type,
        "tokenChange": token,
        "apiURLChange": api,
    }

    for i, j in replace.items():
        text = text.replace(i, j)

    with tempfile.NamedTemporaryFile() as fp:
        with open(fp.name, "w") as f:
            f.write(text)
            f.write("\n")

        return FileResponse(
            open(fp.name, "rb"), as_attachment=True, filename="linux_agent_install.sh"
        )
