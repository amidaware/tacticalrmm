import asyncio
import re
import urllib.parse
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from packaging import version as pyver

from checks.models import CheckResult
from core.utils import get_core_settings, get_mesh_device_id, get_mesh_ws_url
from tacticalrmm.constants import (
    AGENT_DEFER,
    AlertSeverity,
    CheckStatus,
    CheckType,
    MeshAgentIdent,
)
from tacticalrmm.helpers import notify_error


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
        f"{core.mesh_site}/meshagents?id={mesh_id}&installflags=2&meshinstall={arch_id}"
    )

    text = Path(settings.LINUX_AGENT_SCRIPT).read_text()

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

    text += "\n"
    with StringIO(text) as fp:
        return FileResponse(
            fp.read(), as_attachment=True, filename="linux_agent_install.sh"
        )


def get_validated_agent(agent_id, min_version="2.10.0"):
    from .models import Agent

    agent = get_object_or_404(Agent.objects.defer(*AGENT_DEFER), agent_id=agent_id)

    if pyver.parse(agent.version) < pyver.parse(min_version):
        return notify_error(
            f"This feature requires agent version {min_version} or higher."
        )

    return agent


def send_nats_command(agent, func: str, payload: dict, timeout: int = 60):
    try:
        data = {"func": func, "payload": payload}
        response = asyncio.run(agent.nats_cmd(data, timeout=timeout))
    except Exception as e:
        return notify_error(f"NATS communication failed: {str(e)}")

    if response == "timeout":
        return notify_error("Unable to contact the agent")

    if isinstance(response, dict) and "error" in response:
        return notify_error(
            f"{func.replace('_', ' ').title()} failed: {response['error']}"
        )

    return response


def calculate_agent_checks(agent) -> dict:
    total, passing, failing, warning, info = 0, 0, 0, 0, 0

    for check in agent.get_checks_with_policies(exclude_overridden=True):
        total += 1
        if (
            not hasattr(check.check_result, "status")
            or isinstance(check.check_result, CheckResult)
            and check.check_result.status == CheckStatus.PASSING
        ):
            passing += 1
        elif (
            isinstance(check.check_result, CheckResult)
            and check.check_result.status == CheckStatus.FAILING
        ):
            alert_severity = (
                check.check_result.alert_severity
                if check.check_type
                in (
                    CheckType.MEMORY,
                    CheckType.CPU_LOAD,
                    CheckType.DISK_SPACE,
                    CheckType.SCRIPT,
                )
                else check.alert_severity
            )
            if alert_severity == AlertSeverity.ERROR:
                failing += 1
            elif alert_severity == AlertSeverity.WARNING:
                warning += 1
            elif alert_severity == AlertSeverity.INFO:
                info += 1

    ret = {
        "total": total,
        "passing": passing,
        "failing": failing,
        "warning": warning,
        "info": info,
        "has_failing_checks": failing > 0 or warning > 0,
    }
    return ret


def is_windows_path(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    if any(x in s for x in ('"', "'", "\n", "\r", "&", "|", ";")):
        return False
    if not re.match(r"^(?:[a-zA-Z]:\\|\\\\)", s):
        return False
    if not s.lower().endswith(".exe"):
        return False
    return True


def is_posix_abs_path(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    if any(x in s for x in ('"', "'", "\n", "\r", "&", "|", ";")):
        return False
    return s.startswith("/")
