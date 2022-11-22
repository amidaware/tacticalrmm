import asyncio
import tempfile
import urllib.parse
from pathlib import Path

from django.conf import settings
from django.http import FileResponse

from core.utils import get_core_settings, get_mesh_device_id, get_mesh_ws_url
from tacticalrmm.constants import MeshAgentIdent


def get_agent_url(*, goarch: str, plat: str, token: str = "") -> str:
    ver = settings.LATEST_AGENT_VER
    if token:
        params = {
            "version": ver,
            "arch": goarch,
            "token": token,
            "plat": plat,
            "api": settings.ALLOWED_HOSTS[0],
        }
        return settings.AGENTS_URL + urllib.parse.urlencode(params)

    return f"https://github.com/amidaware/rmmagent/releases/download/v{ver}/tacticalagent-v{ver}-{plat}-{goarch}.exe"


def generate_linux_install(
    client: str,
    site: str,
    agent_type: str,
    arch: str,
    token: str,
    api: str,
    download_url: str,
    download_only: bool = False,
) -> FileResponse:

    text = Path(settings.LINUX_AGENT_SCRIPT).read_text()

    # replace contents
    if not download_only:
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
        mesh_dl = f"{core.mesh_site}/meshagents?id={mesh_id}&installflags=2&meshinstall={arch_id}"

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


def generate_linux_install_command(
    install_flags: list,
    arch: str,
    curl_url: str,
    download_url: str,
):
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
        f"{core.mesh_site}/meshagents?id={mesh_id}&installflags=2&meshinstall={arch_id}"
    )

    install_flags.extend(["--meshdl", f"'{mesh_dl}'", "--agentdl", f"'{download_url}'"])
    return f"curl -FL '{curl_url}' | sudo bash -s -- " + " ".join(
        str(i) for i in install_flags
    )
