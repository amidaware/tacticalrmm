import asyncio
import tempfile
import urllib.parse

from core.models import CodeSignToken, CoreSettings
from core.utils import get_mesh_device_id, get_mesh_ws_url
from django.conf import settings
from django.http import FileResponse

from tacticalrmm.constants import MeshAgentIdent


def get_agent_url(arch: str, plat: str) -> str:

    print(arch)
    print(plat)
    if plat == "windows":
        endpoint = "winagents"
        dl_url = settings.DL_32 if arch == "32" else settings.DL_64
    elif plat == "linux":
        endpoint = "linuxagents"
        if arch == "amd64":
            dl_url = settings.LINUX_64
        elif arch == "386":
            dl_url = settings.LINUX_32
        elif arch == "arm64":
            dl_url = settings.LINUX_ARM64
        elif arch == "arm":
            dl_url = settings.LINUX_ARM32
        else:
            dl_url = ""
    elif plat == "macos":
        endpoint = "macos"
        dl_url = ""
    else:
        dl_url = ""

    try:
        t: CodeSignToken = CodeSignToken.objects.first()  # type: ignore
        if t.is_valid:
            base_url = settings.EXE_GEN_URL + f"/api/v1/{endpoint}/?"
            params = {
                "version": settings.LATEST_AGENT_VER,
                "arch": arch,
                "token": t.token,
            }
            dl_url = base_url + urllib.parse.urlencode(params)
    except:
        pass

    print("DL URL")
    print(dl_url)

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

    core: CoreSettings = CoreSettings.objects.first()  # type: ignore

    uri = get_mesh_ws_url()
    mesh_id = asyncio.run(get_mesh_device_id(uri, core.mesh_device_group))
    mesh_dl = f"{core.mesh_site}/meshagents?id={mesh_id}&installflags=0&meshinstall={arch_id}"  # type: ignore

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
