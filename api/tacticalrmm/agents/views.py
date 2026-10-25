import asyncio
import datetime as dt
import json
import random
import string
import time
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from django.utils.dateparse import parse_datetime
from meshctrl.utils import get_login_token
from packaging import version as pyver
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.utils import get_agent_url
from core.models import CoreSettings
from core.permissions import RunServerScriptPerms
from core.tasks import sync_mesh_perms_task
from core.utils import (
    get_core_settings,
    get_mesh_ws_url,
    remove_mesh_agent,
    token_is_valid,
    wake_on_lan,
)
from logs.models import AuditLog, DebugLog, PendingAction
from scripts.models import Script
from scripts.tasks import bulk_command_task, bulk_script_task
from tacticalrmm.constants import (
    AGENT_DARWIN_SHELL_TOKENS,
    AGENT_DEFER,
    AGENT_LINUX_SHELL_TOKENS,
    AGENT_STATUS_OFFLINE,
    AGENT_STATUS_ONLINE,
    AGENT_WINDOWS_SHELL_TOKENS,
    FILE_TRANSFER_ACK_CHECKPOINT_BYTES,
    FILE_TRANSFER_CHUNK_SIZE,
    FILE_TRANSFER_CHUNK_SIZE_MAX,
    FILE_TRANSFER_CHUNK_SIZE_MIN,
    FILE_TRANSFER_PIPELINE_DEPTH,
    FILE_TRANSFER_MAX_SESSIONS_PER_AGENT,
    FILE_TRANSFER_MAX_SESSIONS_PER_USER,
    FILE_TRANSFER_SESSION_TTL_HOURS,
    FILE_BROWSER_DEFAULT_PAGE_SIZE,
    FILE_BROWSER_MAX_PAGE,
    FILE_BROWSER_MAX_PAGE_SIZE,
    FILE_BROWSER_MAX_UPLOAD_FILE_SIZE_BYTES,
    FILE_BROWSER_MAX_ARCHIVE_PATHS,
    FILE_BROWSER_MAX_ARCHIVE_FILES,
    FILE_BROWSER_MAX_ARCHIVE_SIZE_BYTES,
    FILE_BROWSER_MAX_ARCHIVE_DEPTH,
    FILE_BROWSER_ARCHIVE_BUILD_TTL_MINUTES,
    FILE_BROWSER_MAX_EXTRACT_FILES,
    FILE_BROWSER_MAX_EXTRACT_SIZE_BYTES,
    FILE_BROWSER_MAX_EXTRACT_DEPTH,
    FILE_TRANSFER_IDLE_EXPIRE_MINUTES,
    FILE_BROWSER_PROPERTIES_MAX_FILES,
    FILE_BROWSER_PROPERTIES_MAX_DEPTH,
    FILE_BROWSER_PROPERTIES_MAX_DURATION_SECONDS,
    FILE_BROWSER_MIN_AGENT_VERSION,
    FILE_BROWSER_MAX_EXISTS_NAMES,
    FileTransferConflictPolicy,
    FileTransferOperation,
    FileTransferStatus,
    AgentHistoryType,
    AgentMonType,
    AgentPlat,
    AgentTerminalShellChoices,
    AuditActionType,
    CustomFieldModel,
    DebugLogType,
    EvtLogNames,
    PAAction,
    PAStatus,
)
from tacticalrmm.helpers import (
    date_is_in_past,
    notify_error,
    notify_retryable,
    notify_serializer_error,
)
from tacticalrmm.logger import logger
from tacticalrmm.pagination import StandardPagination
from tacticalrmm.permissions import (
    _has_perm_on_agent,
    _has_partial_perm_on_client,
    _has_perm_on_site,
)
from tacticalrmm.utils import get_default_timezone, reload_nats
from winupdate.models import WinUpdate, WinUpdatePolicy
from winupdate.serializers import WinUpdatePolicySerializer
from winupdate.tasks import bulk_check_for_updates_task, bulk_install_updates_task

from .models import (
    Agent,
    AgentCustomField,
    AgentHistory,
    FileTransferSession,
    Note,
)
from .permissions import (
    AgentFileBrowserPerms,
    AgentHistoryPerms,
    AgentNotesPerms,
    AgentPerms,
    AgentRegistryPerms,
    AgentTerminalPerms,
    AgentWOLPerms,
    EvtLogPerms,
    InstallAgentPerms,
    ManageProcPerms,
    MeshPerms,
    RebootAgentPerms,
    RecoverAgentPerms,
    RunBulkPerms,
    RunScriptPerms,
    SendCMDPerms,
    UpdateAgentPerms,
)
from .serializers import (
    AgentCustomFieldSerializer,
    AgentHistorySerializer,
    AgentHostnameSerializer,
    AgentNoteSerializer,
    AgentSerializer,
    AgentTableSerializer,
    AgentFileBrowserDefaultsSerializer,
    AgentTerminalDefaultsSerializer,
    InitFileDownloadArchiveSerializer,
    InitFileDownloadSerializer,
    InitFileUploadSerializer,
)
from .tasks import (
    EXTRACT_EXPIRED_MESSAGE,
    bulk_recover_agents_task,
    run_script_email_results_task,
    send_agent_update_task,
)
from .file_transfer_relay import (
    clear_download_session_redis,
    clear_upload_session_redis,
    delete_download_chunk,
    get_accepted_offset,
    get_download_ack,
    get_download_offered_offset,
    get_upload_ack,
    peek_download_chunk,
    pipeline_depth_full,
    rollback_upload_chunk,
    signal_download_ack,
    store_upload_chunk,
)
from .utils import (
    NATS_FAILED_PREFIX,
    NATS_UNAVAILABLE_MESSAGE,
    get_validated_agent,
    normalize_file_browser_delete_results,
    normalize_file_browser_item,
    normalize_file_browser_items,
    normalize_file_browser_properties,
    parse_upload_content_range,
    resolve_upload_destination_path,
    send_nats_command,
    send_nats_notification,
    collect_file_transfer_paths,
    canonical_file_browser_path,
    canonical_file_browser_paths,
    normalize_file_browser_path,
    validate_absolute_agent_path,
    validate_file_browser_name,
    sanitize_file_browser_name_filter,
    validate_file_transfer_destination_path,
    validate_file_transfer_filename,
    validate_file_transfer_source_path,
    derive_archive_download_filename,
)


class GetAgents(APIView):
    permission_classes = [IsAuthenticated, AgentPerms]

    def get(self, request):
        monitoring_type_filter = Q()
        client_site_filter = Q()

        monitoring_type = request.query_params.get("monitoring_type", None)
        if monitoring_type:
            if monitoring_type in AgentMonType.values:
                monitoring_type_filter = Q(monitoring_type=monitoring_type)
            else:
                return notify_error("monitoring type does not exist")

        if "site" in request.query_params.keys():
            client_site_filter = Q(site_id=request.query_params["site"])
        elif "client" in request.query_params.keys():
            client_site_filter = Q(site__client_id=request.query_params["client"])

        # by default detail=true
        if (
            "detail" not in request.query_params.keys()
            or "detail" in request.query_params.keys()
            and request.query_params["detail"] == "true"
        ):
            agents = (
                Agent.objects.filter_by_role(request.user)  # type: ignore
                .filter(monitoring_type_filter)
                .filter(client_site_filter)
                .select_related(
                    "site__client",
                    "policy",
                    "alert_template",
                )
                .prefetch_related(
                    Prefetch(
                        "custom_fields",
                        queryset=AgentCustomField.objects.select_related("field"),
                    ),
                )
                .annotate(
                    has_patches_pending=Exists(
                        WinUpdate.objects.filter(
                            agent_id=OuterRef("pk"), action="approve", installed=False
                        )
                    ),
                    _pending_actions_count=Count(
                        "pendingactions",
                        filter=Q(pendingactions__status=PAStatus.PENDING),
                    ),
                )
                .defer(
                    "services",
                    "created_by",
                    "created_time",
                    "modified_by",
                    "modified_time",
                )
            )
            serializer = AgentTableSerializer(agents, many=True)

        # if detail=false
        else:
            agents = (
                Agent.objects.filter_by_role(request.user)  # type: ignore
                .defer(*AGENT_DEFER)
                .select_related("site__client")
                .filter(monitoring_type_filter)
                .filter(client_site_filter)
            )
            serializer = AgentHostnameSerializer(agents, many=True)

        return Response(serializer.data)


class GetUpdateDeleteAgent(APIView):
    permission_classes = [IsAuthenticated, AgentPerms]

    class InputSerializer(serializers.ModelSerializer):
        def validate(self, attrs):
            agent = self.instance
            shell = attrs.get("default_shell", getattr(agent, "default_shell", None))
            custom = attrs.get(
                "default_shell_custom", getattr(agent, "default_shell_custom", "")
            )

            shell = (shell or "").strip().lower()
            custom = (custom or "").strip()

            if shell in ("", "none", "null"):
                shell = AgentTerminalShellChoices.USE_GLOBAL
                attrs["default_shell"] = AgentTerminalShellChoices.USE_GLOBAL

            if agent.plat == AgentPlat.WINDOWS:
                allowed = AGENT_WINDOWS_SHELL_TOKENS
                msg = (
                    "Invalid default shell for Windows agent. "
                    "Use global default, 'cmd', 'powershell' or 'custom'."
                )
            elif agent.plat == AgentPlat.LINUX:
                allowed = AGENT_LINUX_SHELL_TOKENS
                msg = (
                    "Invalid default shell for Linux agent. "
                    "Use global default, 'bash' or 'custom'."
                )
            elif agent.plat == AgentPlat.DARWIN:
                allowed = AGENT_DARWIN_SHELL_TOKENS
                msg = (
                    "Invalid default shell for macOS agent. "
                    "Use global default, 'bash' or 'custom'."
                )
            else:
                allowed = {AgentTerminalShellChoices.USE_GLOBAL}
                msg = "Invalid default shell for this agent OS."

            if shell not in allowed:
                raise serializers.ValidationError({"default_shell": msg})

            if shell == AgentTerminalShellChoices.CUSTOM and not custom:
                raise serializers.ValidationError(
                    {"default_shell_custom": "Custom shell path must be provided."}
                )

            attrs["default_shell"] = shell
            return attrs

        class Meta:
            model = Agent
            fields = [
                "maintenance_mode",  # TODO separate this
                "policy",  # TODO separate this
                "block_policy_inheritance",  # TODO separate this
                "monitoring_type",
                "description",
                "overdue_email_alert",
                "overdue_text_alert",
                "overdue_dashboard_alert",
                "offline_time",
                "overdue_time",
                "check_interval",
                "time_zone",
                "site",
                "default_shell",
                "default_shell_custom",
            ]

    # get agent details
    def get(self, request, agent_id):
        from checks.models import Check, CheckResult

        agent = get_object_or_404(
            Agent.objects.select_related(
                "site__server_policy",
                "site__workstation_policy",
                "site__client__server_policy",
                "site__client__workstation_policy",
                "policy",
                "alert_template",
            ).prefetch_related(
                Prefetch(
                    "agentchecks",
                    queryset=Check.objects.select_related("script"),
                ),
                Prefetch(
                    "checkresults",
                    queryset=CheckResult.objects.select_related("assigned_check"),
                ),
                Prefetch(
                    "custom_fields",
                    queryset=AgentCustomField.objects.select_related("field"),
                ),
                Prefetch(
                    "winupdatepolicy",
                    queryset=WinUpdatePolicy.objects.select_related("agent", "policy"),
                ),
            ),
            agent_id=agent_id,
        )
        return Response(AgentSerializer(agent).data)

    # edit agent
    def put(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)

        s = self.InputSerializer(instance=agent, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()

        if "winupdatepolicy" in request.data.keys():
            policy = agent.winupdatepolicy.get()  # type: ignore
            p_serializer = WinUpdatePolicySerializer(
                instance=policy, data=request.data["winupdatepolicy"][0]
            )
            p_serializer.is_valid(raise_exception=True)
            p_serializer.save()

        if "custom_fields" in request.data.keys():
            for field in request.data["custom_fields"]:
                custom_field = field
                custom_field["agent"] = agent.pk

                if AgentCustomField.objects.filter(
                    field=field["field"], agent=agent.pk
                ):
                    value = AgentCustomField.objects.get(
                        field=field["field"], agent=agent.pk
                    )
                    serializer = AgentCustomFieldSerializer(
                        instance=value, data=custom_field
                    )
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                else:
                    serializer = AgentCustomFieldSerializer(data=custom_field)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()

        sync_mesh_perms_task.delay()
        return Response("The agent was updated successfully")

    # uninstall agent
    def delete(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)

        code = "foo"  # stub for windows
        if agent.plat == AgentPlat.LINUX:
            code = Path(settings.LINUX_AGENT_SCRIPT).read_text()
        elif agent.plat == AgentPlat.DARWIN:
            code = Path(settings.MAC_UNINSTALL).read_text()

        asyncio.run(agent.nats_cmd({"func": "uninstall", "code": code}, wait=False))
        name = agent.hostname
        mesh_id = agent.mesh_node_id
        agent.delete()
        reload_nats()
        try:
            uri = get_mesh_ws_url()
            asyncio.run(remove_mesh_agent(uri, mesh_id))
        except Exception as e:
            DebugLog.error(
                message=f"Unable to remove agent {name} from meshcentral database: {e}",
                log_type=DebugLogType.AGENT_ISSUES,
            )
        sync_mesh_perms_task.delay()
        return Response(f"{name} will now be uninstalled.")


class AgentProcesses(APIView):
    permission_classes = [IsAuthenticated, ManageProcPerms]

    # list agent processes
    def get(self, request, agent_id):
        if getattr(settings, "DEMO", False):
            from tacticalrmm.demo_views import demo_get_procs

            return demo_get_procs()

        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd(data={"func": "procs"}, timeout=5))
        if r in ("timeout", "natsdown"):
            return notify_error("Unable to contact the agent")
        return Response(r)

    # kill agent process
    def delete(self, request, agent_id, pid):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(
            agent.nats_cmd({"func": "killproc", "procpid": int(pid)}, timeout=15)
        )

        if r in ("timeout", "natsdown"):
            return notify_error("Unable to contact the agent")
        elif r != "ok":
            return notify_error(r)

        return Response(f"Process with PID: {pid} was ended successfully")


class WebVNC(APIView):
    permission_classes = [IsAuthenticated, MeshPerms]

    def get(self, request, agent_id, port):
        from urllib.parse import urlparse

        from core.mesh_utils import MeshSync

        agent = get_object_or_404(
            Agent.objects.select_related("site__client").defer(*AGENT_DEFER),
            agent_id=agent_id,
        )
        if agent.hex_mesh_node_id == "error":
            return notify_error("Missing mesh node id")

        core = get_core_settings()

        uri = get_mesh_ws_url()
        ms = MeshSync(uri)

        payload = {
            "action": "getcookie",
            "name": None,
            "nodeid": f"node//{agent.hex_mesh_node_id}",
            "tag": "novnc",
            "tcpaddr": None,
            "tcpport": int(port),
        }
        cookie_ret = ms.mesh_action(payload=payload, wait=True)

        vnc_url = (
            core.mesh_site
            + "/novnc/vnc.html?ws=wss%3A%2F%2F"
            + urlparse(core.mesh_site).netloc
            + "%2F"
            + "meshrelay.ashx%3Fauth%3D"
            + cookie_ret["cookie"]  # type: ignore
            + f"&show_dot=1&l=en&resize=scale&name={agent.hostname}"
        )

        ret = {
            "hostname": agent.hostname,
            "vnc": vnc_url,
            "client": agent.client.name,
            "site": agent.site.name,
        }
        return Response(ret)


class AgentMeshCentral(APIView):
    permission_classes = [IsAuthenticated, MeshPerms]

    # get mesh urls
    def get(self, request, agent_id):
        agent = get_object_or_404(
            Agent.objects.select_related("site__client").defer(*AGENT_DEFER),
            agent_id=agent_id,
        )
        core = get_core_settings()

        user = (
            request.user.mesh_user_id
            if core.sync_mesh_with_trmm
            else f"user//{core.mesh_api_superuser}"
        )
        token = get_login_token(key=core.mesh_token, user=user)
        token_param = f"login={token}&"

        control = f"{core.mesh_site}/?{token_param}gotonode={agent.mesh_node_id}&viewmode=11&hide=31"
        terminal = f"{core.mesh_site}/?{token_param}gotonode={agent.mesh_node_id}&viewmode=12&hide=31"
        file = f"{core.mesh_site}/?{token_param}gotonode={agent.mesh_node_id}&viewmode=13&hide=31"

        AuditLog.audit_mesh_session(
            username=request.user.username,
            agent=agent,
            debug_info={"ip": request._client_ip},
        )

        ret = {
            "hostname": agent.hostname,
            "control": control,
            "terminal": terminal,
            "file": file,
            "status": agent.status,
            "client": agent.client.name,
            "site": agent.site.name,
        }
        return Response(ret)

    # start mesh recovery
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        data = {"func": "recover", "payload": {"mode": "mesh"}}
        r = asyncio.run(agent.nats_cmd(data, timeout=90))
        if r != "ok":
            return notify_error("Unable to contact the agent")

        return Response(f"Repaired mesh agent on {agent.hostname}")


@api_view(["GET"])
@permission_classes([IsAuthenticated, AgentPerms])
def get_agent_versions(request):
    agents = (
        Agent.objects.defer(*AGENT_DEFER)
        .filter_by_role(request.user)  # type: ignore
        .select_related("site__client")
    )
    return Response(
        {
            "versions": [settings.LATEST_AGENT_VER],
            "agents": AgentHostnameSerializer(agents, many=True).data,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, UpdateAgentPerms])
def update_agents(request):
    q = (
        Agent.objects.filter_by_role(request.user)  # type: ignore
        .filter(agent_id__in=request.data["agent_ids"])
        .only("agent_id", "version")
    )
    agent_ids: list[str] = [
        i.agent_id
        for i in q
        if pyver.parse(i.version) < pyver.parse(settings.LATEST_AGENT_VER)
    ]

    token, _ = token_is_valid()
    send_agent_update_task.delay(agent_ids=agent_ids, token=token, force=False)
    return Response("ok")


@api_view(["GET"])
@permission_classes([IsAuthenticated, AgentPerms])
def ping(request, agent_id):
    agent = get_object_or_404(Agent, agent_id=agent_id)
    status = AGENT_STATUS_OFFLINE
    attempts = 0
    while 1:
        r = asyncio.run(agent.nats_cmd({"func": "ping"}, timeout=2))
        if r == "pong":
            status = AGENT_STATUS_ONLINE
            break
        else:
            attempts += 1
            time.sleep(0.5)

        if attempts >= 3:
            break

    return Response({"name": agent.hostname, "status": status})


@api_view(["GET"])
@permission_classes([IsAuthenticated, EvtLogPerms])
def get_event_log(request, agent_id, logtype, days):
    if getattr(settings, "DEMO", False):
        from tacticalrmm.demo_views import demo_get_eventlog

        return demo_get_eventlog()

    agent = get_object_or_404(Agent, agent_id=agent_id)
    timeout = 180 if logtype == EvtLogNames.SECURITY else 30

    data = {
        "func": "eventlog",
        "timeout": timeout,
        "payload": {
            "logname": logtype,
            "days": str(days),
        },
    }
    r = asyncio.run(agent.nats_cmd(data, timeout=timeout + 2))
    if r in ("timeout", "natsdown"):
        return notify_error("Unable to contact the agent")

    return Response(r)


@api_view(["POST"])
@permission_classes([IsAuthenticated, SendCMDPerms])
def send_raw_cmd(request, agent_id):
    agent = get_object_or_404(Agent, agent_id=agent_id)
    timeout = int(request.data["timeout"])
    if request.data["shell"] == "custom" and request.data["custom_shell"]:
        shell = request.data["custom_shell"]
    else:
        shell = request.data["shell"]

    data = {
        "func": "rawcmd",
        "timeout": timeout,
        "payload": {
            "command": request.data["cmd"],
            "shell": shell,
        },
        "run_as_user": request.data["run_as_user"],
    }

    hist = AgentHistory.objects.create(
        agent=agent,
        type=AgentHistoryType.CMD_RUN,
        command=request.data["cmd"],
        username=request.user.username[:50],
    )
    data["id"] = hist.pk

    r = asyncio.run(agent.nats_cmd(data, timeout=timeout + 2))

    if r == "timeout":
        return notify_error("Unable to contact the agent")

    AuditLog.audit_raw_command(
        username=request.user.username,
        agent=agent,
        cmd=request.data["cmd"],
        shell=shell,
        debug_info={"ip": request._client_ip},
    )

    return Response(r)


class Shutdown(APIView):
    permission_classes = [IsAuthenticated, RebootAgentPerms]

    # shutdown
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "shutdown"}, timeout=10))
        if r != "ok":
            return notify_error("Unable to contact the agent")

        return Response("ok")


class Reboot(APIView):
    permission_classes = [IsAuthenticated, RebootAgentPerms]

    # reboot now
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "rebootnow"}, timeout=10))
        if r != "ok":
            return notify_error("Unable to contact the agent")

        return Response("ok")

    # reboot later
    def patch(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        if agent.is_posix:
            return notify_error(f"Not currently implemented for {agent.plat}")

        try:
            obj = dt.datetime.strptime(request.data["datetime"], "%Y-%m-%dT%H:%M")
        except Exception:
            return notify_error("Invalid date")

        if date_is_in_past(datetime_obj=obj, agent_tz=agent.timezone):
            return notify_error("Date cannot be set in the past")

        task_name = "TacticalRMM_SchedReboot_" + "".join(
            random.choice(string.ascii_letters) for _ in range(10)
        )

        expire_date = obj + djangotime.timedelta(minutes=5)

        nats_data = {
            "func": "schedtask",
            "schedtaskpayload": {
                "type": "schedreboot",
                "enabled": True,
                "delete_expired_task_after": True,
                "start_when_available": False,
                "multiple_instances": 2,
                "trigger": "runonce",
                "name": task_name,
                "start_year": int(dt.datetime.strftime(obj, "%Y")),
                "start_month": int(dt.datetime.strftime(obj, "%-m")),
                "start_day": int(dt.datetime.strftime(obj, "%-d")),
                "start_hour": int(dt.datetime.strftime(obj, "%-H")),
                "start_min": int(dt.datetime.strftime(obj, "%-M")),
                "expire_year": int(expire_date.strftime("%Y")),
                "expire_month": int(expire_date.strftime("%-m")),
                "expire_day": int(expire_date.strftime("%-d")),
                "expire_hour": int(expire_date.strftime("%-H")),
                "expire_min": int(expire_date.strftime("%-M")),
            },
        }

        r = asyncio.run(agent.nats_cmd(nats_data, timeout=10))
        if r != "ok":
            return notify_error(r)

        details = {"taskname": task_name, "time": str(obj)}
        PendingAction.objects.create(
            agent=agent, action_type=PAAction.SCHED_REBOOT, details=details
        )
        nice_time = dt.datetime.strftime(obj, "%B %d, %Y at %I:%M %p")
        return Response(
            {"time": nice_time, "agent": agent.hostname, "task_name": task_name}
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated, InstallAgentPerms])
def install_agent(request):
    from knox.models import AuthToken

    from accounts.models import User
    from core.utils import token_is_valid

    insecure = getattr(settings, "TRMM_INSECURE", False)

    if insecure and request.data["installMethod"] in {"exe", "powershell"}:
        return notify_error(
            "Not available in insecure mode. Please use the 'Manual' method."
        )

    # TODO rework this ghetto validation hack
    # https://github.com/amidaware/tacticalrmm/issues/1461
    try:
        int(request.data["expires"])
    except ValueError:
        return notify_error("Please enter a valid number of hours")

    client_id = request.data["client"]
    site_id = request.data["site"]
    version = settings.LATEST_AGENT_VER
    goarch = request.data["goarch"]
    plat = request.data["plat"]

    if not _has_perm_on_site(request.user, site_id):
        raise PermissionDenied()

    codesign_token, is_valid = token_is_valid()

    if request.data["installMethod"] in {"bash", "mac"} and not is_valid:
        return notify_error(
            "Linux/Mac agents require code signing. Please see https://docs.tacticalrmm.com/code_signing/ for more info."
        )

    inno = f"tacticalagent-v{version}-{plat}-{goarch}"
    if plat == AgentPlat.WINDOWS:
        inno += ".exe"

    download_url = get_agent_url(goarch=goarch, plat=plat, token=codesign_token)

    installer_user = User.objects.filter(is_installer_user=True).first()

    _, token = AuthToken.objects.create(
        user=installer_user, expiry=dt.timedelta(hours=int(request.data["expires"]))
    )

    install_flags = [
        "-m",
        "install",
        "--api",
        request.data["api"],
        "--client-id",
        client_id,
        "--site-id",
        site_id,
        "--agent-type",
        request.data["agenttype"],
        "--auth",
        token,
    ]

    if request.data["installMethod"] == "exe":
        from tacticalrmm.utils import generate_winagent_exe

        return generate_winagent_exe(
            client=client_id,
            site=site_id,
            agent_type=request.data["agenttype"],
            rdp=request.data["rdp"],
            ping=request.data["ping"],
            power=request.data["power"],
            goarch=goarch,
            token=token,
            api=request.data["api"],
            file_name=request.data["fileName"],
        )

    elif request.data["installMethod"] == "bash":
        from agents.utils import generate_linux_install

        return generate_linux_install(
            client=str(client_id),
            site=str(site_id),
            agent_type=request.data["agenttype"],
            arch=goarch,
            token=token,
            api=request.data["api"],
            download_url=download_url,
        )

    elif request.data["installMethod"] in {"manual", "mac"}:
        resp = {}
        if request.data["installMethod"] == "manual":
            cmd = [
                inno,
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "&&",
                "ping",
                "127.0.0.1",
                "-n",
                "7",
                "&&",
                r'"C:\Program Files\TacticalAgent\tacticalrmm.exe"',
            ] + install_flags

            if int(request.data["rdp"]):
                cmd.append("--rdp")
            if int(request.data["ping"]):
                cmd.append("--ping")
            if int(request.data["power"]):
                cmd.append("--power")

            if insecure:
                cmd.append("--insecure")

            resp["cmd"] = " ".join(str(i) for i in cmd)
        else:
            install_flags.insert(0, f"sudo ./{inno}")
            cmd = install_flags.copy()
            dl = f"curl -L -o {inno} '{download_url}'"
            resp["cmd"] = (
                dl + f" && chmod +x {inno} && " + " ".join(str(i) for i in cmd)
            )
            if insecure:
                resp["cmd"] += " --insecure"

        resp["url"] = download_url

        return Response(resp)

    elif request.data["installMethod"] == "powershell":
        text = Path(settings.BASE_DIR / "core" / "installer.ps1").read_text()

        replace_dict = {
            "innosetupchange": inno,
            "clientchange": str(client_id),
            "sitechange": str(site_id),
            "apichange": request.data["api"],
            "atypechange": request.data["agenttype"],
            "powerchange": str(request.data["power"]),
            "rdpchange": str(request.data["rdp"]),
            "pingchange": str(request.data["ping"]),
            "downloadchange": download_url,
            "tokenchange": token,
        }

        for i, j in replace_dict.items():
            text = text.replace(i, j)

        with StringIO(text) as fp:
            response = HttpResponse(fp.read(), content_type="text/plain")
            response["Content-Disposition"] = "attachment; filename=rmm-installer.ps1"
            return response


@api_view(["POST"])
@permission_classes([IsAuthenticated, RecoverAgentPerms])
def recover(request, agent_id: str) -> Response:
    agent: Agent = get_object_or_404(
        Agent.objects.defer(*AGENT_DEFER), agent_id=agent_id
    )
    mode = request.data["mode"]

    if mode == "tacagent":
        uri = get_mesh_ws_url()
        code_token, _ = token_is_valid()
        agent_url = get_agent_url(
            goarch=agent.goarch, plat=agent.plat, token=code_token
        )
        agent.recover(mode, uri, wait=False, agent_url=agent_url)
        return Response("Recovery will be attempted shortly")

    elif mode == "mesh":
        r, err = agent.recover(mode, "")
        if err:
            return notify_error(f"Unable to complete recovery: {r}")

    return Response("Successfully completed recovery")


@api_view(["POST"])
@permission_classes([IsAuthenticated, RunScriptPerms])
def run_script(request, agent_id):
    agent = get_object_or_404(Agent, agent_id=agent_id)
    script = get_object_or_404(Script, pk=request.data["script"])
    output = request.data["output"]
    args = request.data["args"]
    run_as_user: bool = request.data["run_as_user"]
    env_vars: list[str] = request.data["env_vars"]
    req_timeout = int(request.data["timeout"]) + 3
    run_on_server: bool | None = request.data.get("run_on_server")

    if run_on_server:
        if not get_core_settings().server_scripts_enabled:
            return notify_error("This feature is disabled.")

        if not RunServerScriptPerms().has_permission(request, None):
            raise PermissionDenied()

    AuditLog.audit_script_run(
        username=request.user.username,
        agent=agent,
        script=script.name,
        debug_info={"ip": request._client_ip},
    )

    hist = AgentHistory.objects.create(
        agent=agent,
        type=AgentHistoryType.SCRIPT_RUN,
        script=script,
        username=request.user.username[:50],
    )
    history_pk = hist.pk

    if run_on_server:
        from core.utils import run_server_script

        r = run_server_script(
            body=script.script_body,
            args=script.parse_script_args(agent, script.shell, args),
            env_vars=script.parse_script_env_vars(agent, script.shell, env_vars),
            shell=script.shell,
            timeout=req_timeout,
        )

        ret = {
            "stdout": r[0],
            "stderr": r[1],
            "execution_time": "{:.4f}".format(r[2]),
            "retcode": r[3],
        }

        hist.script_results = {**ret, "id": history_pk}
        hist.save(update_fields=["script_results"])

        return Response(ret)

    if output == "wait":
        r = agent.run_script(
            scriptpk=script.pk,
            args=args,
            timeout=req_timeout,
            wait=True,
            history_pk=history_pk,
            run_as_user=run_as_user,
            env_vars=env_vars,
        )
        return Response(r)

    elif output == "email":
        emails = (
            [] if request.data["emailMode"] == "default" else request.data["emails"]
        )
        run_script_email_results_task.delay(
            agentpk=agent.pk,
            scriptpk=script.pk,
            nats_timeout=req_timeout,
            emails=emails,
            args=args,
            history_pk=history_pk,
            run_as_user=run_as_user,
            env_vars=env_vars,
        )
    elif output == "collector":
        from core.models import CustomField

        r = agent.run_script(
            scriptpk=script.pk,
            args=args,
            timeout=req_timeout,
            wait=True,
            history_pk=history_pk,
            run_as_user=run_as_user,
            env_vars=env_vars,
        )

        custom_field = CustomField.objects.get(pk=request.data["custom_field"])

        if custom_field.model == CustomFieldModel.AGENT:
            field = custom_field.get_or_create_field_value(agent)
        elif custom_field.model == CustomFieldModel.CLIENT:
            field = custom_field.get_or_create_field_value(agent.client)
        elif custom_field.model == CustomFieldModel.SITE:
            field = custom_field.get_or_create_field_value(agent.site)
        else:
            return notify_error("Custom Field was invalid")

        value = (
            r.strip()
            if request.data["save_all_output"]
            else r.strip().split("\n")[-1].strip()
        )

        field.save_to_field(value)
        return Response(r)
    elif output == "note":
        r = agent.run_script(
            scriptpk=script.pk,
            args=args,
            timeout=req_timeout,
            wait=True,
            history_pk=history_pk,
            run_as_user=run_as_user,
            env_vars=env_vars,
        )

        Note.objects.create(agent=agent, user=request.user, note=r)
        return Response(r)
    else:
        agent.run_script(
            scriptpk=script.pk,
            args=args,
            timeout=req_timeout,
            history_pk=history_pk,
            run_as_user=run_as_user,
            env_vars=env_vars,
        )

    return Response(f"{script.name} will now be run on {agent.hostname}")


class GetAddNotes(APIView):
    permission_classes = [IsAuthenticated, AgentNotesPerms]

    def get(self, request, agent_id=None):
        if agent_id:
            agent = get_object_or_404(Agent, agent_id=agent_id)
            notes = Note.objects.filter(agent=agent)
        else:
            notes = Note.objects.filter_by_role(request.user)  # type: ignore

        return Response(AgentNoteSerializer(notes, many=True).data)

    def post(self, request):
        agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        if not _has_perm_on_agent(request.user, agent.agent_id):
            raise PermissionDenied()

        if "note" not in request.data.keys():
            return notify_error("Cannot add an empty note")

        data = {
            "note": request.data["note"],
            "agent": agent.pk,
            "user": request.user.pk,
        }

        serializer = AgentNoteSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("Note added!")


class GetEditDeleteNote(APIView):
    permission_classes = [IsAuthenticated, AgentNotesPerms]

    def get(self, request, pk):
        note = get_object_or_404(Note, pk=pk)

        if not _has_perm_on_agent(request.user, note.agent.agent_id):
            raise PermissionDenied()

        return Response(AgentNoteSerializer(note).data)

    def put(self, request, pk):
        note = get_object_or_404(Note, pk=pk)

        if not _has_perm_on_agent(request.user, note.agent.agent_id):
            raise PermissionDenied()

        serializer = AgentNoteSerializer(instance=note, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("Note edited!")

    def delete(self, request, pk):
        note = get_object_or_404(Note, pk=pk)

        if not _has_perm_on_agent(request.user, note.agent.agent_id):
            raise PermissionDenied()

        note.delete()
        return Response("Note was deleted!")


@api_view(["POST"])
@permission_classes([IsAuthenticated, RunBulkPerms])
def bulk(request):
    if request.data["target"] == "agents" and not request.data["agents"]:
        return notify_error("Must select at least 1 agent")

    if request.data["target"] == "client":
        if not _has_partial_perm_on_client(request.user, request.data["client"]):
            raise PermissionDenied()
        q = Agent.objects.filter_by_role(request.user).filter(  # type: ignore
            site__client_id=request.data["client"]
        )

    elif request.data["target"] == "site":
        if not _has_perm_on_site(request.user, request.data["site"]):
            raise PermissionDenied()
        q = Agent.objects.filter_by_role(request.user).filter(  # type: ignore
            site_id=request.data["site"]
        )

    elif request.data["target"] == "agents":
        q = Agent.objects.filter_by_role(request.user).filter(  # type: ignore
            agent_id__in=request.data["agents"]
        )

    elif request.data["target"] == "all":
        q = Agent.objects.filter_by_role(request.user).only("pk", "monitoring_type")  # type: ignore

    else:
        return notify_error("Something went wrong")

    if request.data["monType"] == "servers":
        q = q.filter(monitoring_type=AgentMonType.SERVER)
    elif request.data["monType"] == "workstations":
        q = q.filter(monitoring_type=AgentMonType.WORKSTATION)

    if request.data["osType"] == AgentPlat.WINDOWS:
        q = q.filter(plat=AgentPlat.WINDOWS)
    elif request.data["osType"] == AgentPlat.LINUX:
        q = q.filter(plat=AgentPlat.LINUX)
    elif request.data["osType"] == AgentPlat.DARWIN:
        q = q.filter(plat=AgentPlat.DARWIN)

    agents: list[int] = [agent.pk for agent in q]

    if not agents:
        return notify_error("No agents were found meeting the selected criteria")

    AuditLog.audit_bulk_action(
        request.user,
        request.data["mode"],
        request.data,
        debug_info={"ip": request._client_ip},
    )

    ht = "Check the History tab on the agent to view the results."

    if request.data["mode"] == "command":
        if request.data["shell"] == "custom" and request.data["custom_shell"]:
            shell = request.data["custom_shell"]
        else:
            shell = request.data["shell"]

        bulk_command_task.delay(
            agent_pks=agents,
            cmd=request.data["cmd"],
            shell=shell,
            timeout=request.data["timeout"],
            username=request.user.username[:50],
            run_as_user=request.data["run_as_user"],
        )
        return Response(f"Command will now be run on {len(agents)} agents. {ht}")

    elif request.data["mode"] == "script":
        script = get_object_or_404(Script, pk=request.data["script"])

        # prevent API from breaking for those who haven't updated payload
        try:
            custom_field_pk = request.data["custom_field"]
            collector_all_output = request.data["collector_all_output"]
            save_to_agent_note = request.data["save_to_agent_note"]
        except KeyError:
            custom_field_pk = None
            collector_all_output = False
            save_to_agent_note = False

        bulk_script_task.delay(
            script_pk=script.pk,
            agent_pks=agents,
            args=request.data["args"],
            timeout=request.data["timeout"],
            username=request.user.username[:50],
            run_as_user=request.data["run_as_user"],
            env_vars=request.data["env_vars"],
            custom_field_pk=custom_field_pk,
            collector_all_output=collector_all_output,
            save_to_agent_note=save_to_agent_note,
        )

        return Response(f"{script.name} will now be run on {len(agents)} agents. {ht}")

    elif request.data["mode"] == "patch":
        if request.data["patchMode"] == "install":
            bulk_install_updates_task.delay(agents)
            return Response(
                f"Pending updates will now be installed on {len(agents)} agents"
            )
        elif request.data["patchMode"] == "scan":
            bulk_check_for_updates_task.delay(agents)
            return Response(f"Patch status scan will now run on {len(agents)} agents")

    return notify_error("Something went wrong")


@api_view(["POST"])
@permission_classes([IsAuthenticated, AgentPerms])
def agent_maintenance(request):
    if request.data["type"] == "Client":
        if not _has_partial_perm_on_client(request.user, request.data["id"]):
            raise PermissionDenied()

        count = (
            Agent.objects.filter_by_role(request.user)  # type: ignore
            .filter(site__client_id=request.data["id"])
            .update(maintenance_mode=request.data["action"])
        )

    elif request.data["type"] == "Site":
        if not _has_perm_on_site(request.user, request.data["id"]):
            raise PermissionDenied()

        count = (
            Agent.objects.filter_by_role(request.user)  # type: ignore
            .filter(site_id=request.data["id"])
            .update(maintenance_mode=request.data["action"])
        )

    else:
        return notify_error("Invalid data")

    if count:
        action = "disabled" if not request.data["action"] else "enabled"
        return Response(f"Maintenance mode has been {action} on {count} agents")

    return Response(
        "No agents have been put in maintenance mode. You might not have permissions to the resources."
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, RecoverAgentPerms])
def bulk_agent_recovery(request):
    bulk_recover_agents_task.delay()
    return Response("Agents will now be recovered")


class WMI(APIView):
    permission_classes = [IsAuthenticated, AgentPerms]

    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "sysinfo"}, timeout=20))
        if r != "ok":
            return notify_error("Unable to contact the agent")
        return Response("Agent WMI data refreshed successfully")


class AgentHistoryView(APIView):
    # TODO deprecated

    permission_classes = [IsAuthenticated, AgentHistoryPerms]

    def get(self, request, agent_id=None):
        if agent_id:
            agent = get_object_or_404(Agent, agent_id=agent_id)
            history = AgentHistory.objects.filter(agent=agent)
        else:
            history = AgentHistory.objects.filter_by_role(request.user)  # type: ignore
        ctx = {"default_tz": get_default_timezone()}
        return Response(AgentHistorySerializer(history, many=True, context=ctx).data)


class AgentHistoryViewV2(APIView):
    permission_classes = [IsAuthenticated, AgentHistoryPerms]
    ordering_fields = ("time", "type", "command", "username")

    def get(self, request, agent_id=None):
        if agent_id:
            agent = get_object_or_404(Agent, agent_id=agent_id)
            history = AgentHistory.objects.filter(agent=agent)
        else:
            history = AgentHistory.objects.filter_by_role(request.user)  # type: ignore

        ordering = request.query_params.get("ordering", "-time")
        if ordering.lstrip("-") not in self.ordering_fields:
            ordering = "-time"
        # id as tiebreaker so rows never shift between pages
        history = history.select_related("script").order_by(ordering, "-id")

        paginator = StandardPagination()
        page = paginator.paginate_queryset(history, request, view=self)
        ctx = {"default_tz": get_default_timezone()}
        serializer = AgentHistorySerializer(page, many=True, context=ctx)
        return paginator.get_paginated_response(serializer.data)


class ScriptRunHistory(APIView):
    permission_classes = [IsAuthenticated, AgentHistoryPerms]

    class OutputSerializer(serializers.ModelSerializer):
        script_name = serializers.ReadOnlyField(source="script.name")
        agent_id = serializers.ReadOnlyField(source="agent.agent_id")

        class Meta:
            model = AgentHistory
            fields = (
                "id",
                "time",
                "username",
                "script",
                "script_results",
                "agent",
                "script_name",
                "agent_id",
            )
            read_only_fields = fields

    def get(self, request):
        date_range_filter = Q()
        script_name_filter = Q()

        start = request.query_params.get("start", None)
        end = request.query_params.get("end", None)
        limit = request.query_params.get("limit", None)
        script_name = request.query_params.get("scriptname", None)
        if start and end:
            start_dt = parse_datetime(start)
            end_dt = parse_datetime(end) + djangotime.timedelta(days=1)
            date_range_filter = Q(time__range=[start_dt, end_dt])

        if script_name:
            script_name_filter = Q(script__name=script_name)

        AGENT_R_DEFER = (
            "agent__wmi_detail",
            "agent__services",
            "agent__created_by",
            "agent__created_time",
            "agent__modified_by",
            "agent__modified_time",
            "agent__disks",
            "agent__operating_system",
            "agent__mesh_node_id",
            "agent__description",
            "agent__patches_last_installed",
            "agent__time_zone",
            "agent__alert_template_id",
            "agent__policy_id",
            "agent__site_id",
            "agent__version",
            "agent__plat",
            "agent__goarch",
            "agent__hostname",
            "agent__last_seen",
            "agent__public_ip",
            "agent__total_ram",
            "agent__boot_time",
            "agent__logged_in_username",
            "agent__last_logged_in_user",
            "agent__monitoring_type",
            "agent__overdue_email_alert",
            "agent__overdue_text_alert",
            "agent__overdue_dashboard_alert",
            "agent__offline_time",
            "agent__overdue_time",
            "agent__check_interval",
            "agent__needs_reboot",
            "agent__choco_installed",
            "agent__maintenance_mode",
            "agent__block_policy_inheritance",
        )
        hists = (
            AgentHistory.objects.filter_by_role(request.user)  # type: ignore
            .select_related("agent")
            .select_related("script")
            .defer(*AGENT_R_DEFER)
            .filter(type=AgentHistoryType.SCRIPT_RUN)
            .filter(date_range_filter)
            .filter(script_name_filter)
            .order_by("-time")
        )
        if limit:
            try:
                lim = int(limit)
            except KeyError:
                return notify_error("Invalid limit")
            hists = hists[:lim]

        ret = self.OutputSerializer(hists, many=True).data
        return Response(ret)


@api_view(["POST"])
@permission_classes([IsAuthenticated, AgentWOLPerms])
def wol(request, agent_id):
    agent = get_object_or_404(
        Agent.objects.defer(*AGENT_DEFER),
        agent_id=agent_id,
    )
    try:
        uri = get_mesh_ws_url()
        asyncio.run(wake_on_lan(uri=uri, mesh_node_id=agent.mesh_node_id))
    except Exception as e:
        return notify_error(str(e))
    return Response(f"Wake-on-LAN sent to {agent.hostname}")


@api_view(["GET"])
@permission_classes([IsAuthenticated, AgentRegistryPerms])
def browse_registry(request, agent_id):
    agent = get_validated_agent(agent_id)
    if isinstance(agent, Response):
        return agent

    path = request.query_params.get("path", "Computer").strip()
    if path.lower() == "computer":
        path = "Computer"

    try:
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 200))
    except ValueError:
        return notify_error("page and page_size must be integers")

    payload = {"path": path, "page": str(page), "page_size": str(page_size)}
    r = send_nats_command(agent, "registry_browse", payload, timeout=30)

    if isinstance(r, Response):
        return r

    return Response(
        {
            "path": r.get("path", path),
            "subkeys": r.get("subkeys", []),
            "values": r.get("values", []),
            "has_more": r.get("has_more", False),
            "page": page,
            "page_size": page_size,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, AgentRegistryPerms])
def create_registry_key(request, agent_id):
    agent = get_validated_agent(agent_id)
    if isinstance(agent, Response):
        return agent

    path = (request.data.get("path") or "").strip()
    if not path:
        return notify_error("Registry path is required")

    payload = {"path": path}
    r = send_nats_command(agent, "registry_create_key", payload, timeout=30)

    if isinstance(r, Response):
        return r

    return Response({"status": "success", "path": path})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, AgentRegistryPerms])
def delete_registry_key(request, agent_id):
    agent = get_validated_agent(agent_id)
    if isinstance(agent, Response):
        return agent

    path = (request.query_params.get("path") or "").strip()
    if not path:
        return notify_error("Registry path is required")

    payload = {"path": path}
    r = send_nats_command(agent, "registry_delete_key", payload, timeout=30)

    if isinstance(r, Response):
        return r

    return Response({"status": "success", "deleted_path": path})


@api_view(["POST"])
@permission_classes([IsAuthenticated, AgentRegistryPerms])
def rename_registry_key(request, agent_id):
    agent = get_validated_agent(agent_id)
    if isinstance(agent, Response):
        return agent

    old_path = (request.data.get("old_path") or "").strip()
    new_path = (request.data.get("new_path") or "").strip()

    if not old_path or not new_path:
        return notify_error("Both 'old_path' and 'new_path' are required")
    if old_path == new_path:
        return notify_error("Old and new path cannot be the same")

    payload = {"old_path": old_path, "new_path": new_path}
    r = send_nats_command(agent, "registry_rename_key", payload, timeout=60)

    if isinstance(r, Response):
        return r

    return Response(
        {
            "status": "success",
            "old_path": old_path,
            "new_path": new_path,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, AgentRegistryPerms])
def create_registry_value(request, agent_id):
    agent = get_validated_agent(agent_id)
    if isinstance(agent, Response):
        return agent

    path = (request.data.get("path") or "").strip()
    val_name = request.data.get("name")
    val_type = (request.data.get("type") or "").strip().upper()
    val_data = request.data.get("data")

    if not path:
        return notify_error("Registry path is required")
    if not val_type:
        return notify_error("Registry value type is required")
    if not val_name:
        return notify_error("Registry value name is required")

    payload = {
        "path": path,
        "type": val_type,
        "name": val_name,
        "data": val_data,
    }

    r = send_nats_command(agent, "registry_create_value", payload, timeout=30)

    if isinstance(r, Response):
        return r

    return Response(
        {
            "status": "success",
            "data": {
                "name": r.get("name", val_name),
                "type": r.get("type", val_type),
                "data": r.get("data", val_data),
            },
        }
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, AgentRegistryPerms])
def delete_registry_value(request, agent_id):
    agent = get_validated_agent(agent_id)
    if isinstance(agent, Response):
        return agent

    path = (request.query_params.get("path") or "").strip()
    val_name = request.query_params.get("name")

    if not path:
        return notify_error("Registry path is required")
    if not val_name:
        return notify_error("Registry value name is required")

    payload = {"path": path, "name": val_name}
    r = send_nats_command(agent, "registry_delete_value", payload, timeout=30)

    if isinstance(r, Response):
        return r

    return Response({"status": "success", "name": val_name})


@api_view(["POST"])
@permission_classes([IsAuthenticated, AgentRegistryPerms])
def rename_registry_value(request, agent_id):
    agent = get_validated_agent(agent_id)
    if isinstance(agent, Response):
        return agent

    path = (request.data.get("path") or "").strip()
    old_name = request.data.get("old_name")
    new_name = request.data.get("new_name")

    if not path:
        return notify_error("Registry path is required")
    if not old_name:
        return notify_error("Old value name is required")
    if not new_name:
        return notify_error("New value name is required")
    if old_name == new_name:
        return notify_error("Old and new value names cannot be the same")

    payload = {
        "path": path,
        "old_name": old_name,
        "new_name": new_name,
    }

    r = send_nats_command(agent, "registry_rename_value", payload, timeout=30)

    if isinstance(r, Response):
        return r

    return Response(
        {
            "status": "success",
            "old_name": old_name,
            "new_name": r.get("new_name", new_name),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, AgentRegistryPerms])
def modify_registry_value(request, agent_id):
    agent = get_validated_agent(agent_id)
    if isinstance(agent, Response):
        return agent

    path = (request.data.get("path") or "").strip()
    val_name = request.data.get("name")
    val_type = (request.data.get("type") or "").strip().upper()
    val_data = request.data.get("data")

    if not path:
        return notify_error("Registry path is required")
    if not val_name:
        return notify_error("Registry value name is required")
    if not val_type:
        return notify_error("Registry value type is required")

    payload = {
        "path": path,
        "name": val_name,
        "type": val_type,
        "data": val_data,
    }

    r = send_nats_command(agent, "registry_modify_value", payload, timeout=30)

    if isinstance(r, Response):
        return r

    return Response(
        {
            "status": "success",
            "data": {
                "name": r.get("name", val_name),
                "type": r.get("type", val_type),
                "data": r.get("data", val_data),
            },
        }
    )


_FILE_TRANSFER_ACTIVE_STATUSES = (
    FileTransferStatus.WAITING_FOR_AGENT,
    FileTransferStatus.AGENT_READY,
    FileTransferStatus.TRANSFERRING,
)


def enforce_file_transfer_session_limits(agent, user):
    base = FileTransferSession.objects.filter(
        status__in=_FILE_TRANSFER_ACTIVE_STATUSES,
        expires_at__gt=djangotime.now(),
    )

    if (
        FILE_TRANSFER_MAX_SESSIONS_PER_AGENT > 0
        and base.filter(agent=agent).count() >= FILE_TRANSFER_MAX_SESSIONS_PER_AGENT
    ):
        return Response(
            "Too many concurrent file transfers for this agent; "
            "wait for an in-progress transfer to finish.",
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if (
        FILE_TRANSFER_MAX_SESSIONS_PER_USER > 0
        and base.filter(user=user).count() >= FILE_TRANSFER_MAX_SESSIONS_PER_USER
    ):
        return Response(
            "Too many concurrent file transfers for this user; "
            "wait for an in-progress transfer to finish.",
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    return None


def create_file_transfer_session_locked(agent, user, **fields):
    """Atomically enforce concurrency caps and create the session."""
    from accounts.models import User
    from agents.tasks import expire_stale_file_transfer_sessions

    with transaction.atomic():
        Agent.objects.select_for_update().filter(pk=agent.pk).first()
        User.objects.select_for_update().filter(pk=user.pk).first()
        expire_stale_file_transfer_sessions(agent=agent, notify_agent=False)
        limit_err = enforce_file_transfer_session_limits(agent, user)
        if limit_err is not None:
            return limit_err
        if fields.get("operation") == FileTransferOperation.UPLOAD:
            busy_err = _upload_destination_busy(agent, fields.get("destination_path"))
            if busy_err is not None:
                return busy_err
        return FileTransferSession.objects.create(agent=agent, user=user, **fields)


def _upload_destination_busy(agent, destination_path):
    """Two uploads to the same file would share the same .partial on the agent."""
    active = FileTransferSession.objects.filter(
        agent=agent,
        operation=FileTransferOperation.UPLOAD,
        status__in=_FILE_TRANSFER_RESUMABLE_STATUSES,
    )
    if agent.plat in (AgentPlat.WINDOWS, AgentPlat.DARWIN):
        active = active.filter(destination_path__iexact=destination_path)
    else:
        active = active.filter(destination_path=destination_path)
    if active.exists():
        return notify_error(
            "Another upload to this file is in progress or paused. "
            "Wait for it, or resume or cancel it, then try again."
        )
    return None


def _normalize_upload_conflict_policy(raw):
    """Return a valid conflict policy, or None when an invalid value."""
    if raw is None:
        return FileTransferConflictPolicy.REPLACE
    val = str(raw).strip().lower()
    if not val:
        return FileTransferConflictPolicy.REPLACE
    if val in FileTransferConflictPolicy.values:
        return val
    return None


def _file_transfer_chunk_size(requested) -> int:
    if requested is None:
        return FILE_TRANSFER_CHUNK_SIZE
    return max(
        FILE_TRANSFER_CHUNK_SIZE_MIN,
        min(int(requested), FILE_TRANSFER_CHUNK_SIZE_MAX),
    )


_FILE_TRANSFER_RESUMABLE_STATUSES = (
    FileTransferStatus.WAITING_FOR_AGENT,
    FileTransferStatus.AGENT_READY,
    FileTransferStatus.TRANSFERRING,
)


def _mark_session_resumed(session: FileTransferSession, committed_offset: int) -> bool:
    """Returns False if the session was cancelled during the agent prepare."""
    now = djangotime.now()
    expires_at = now + dt.timedelta(hours=FILE_TRANSFER_SESSION_TTL_HOURS)
    updated = FileTransferSession.objects.filter(
        pk=session.pk, status__in=_FILE_TRANSFER_RESUMABLE_STATUSES
    ).update(
        status=FileTransferStatus.AGENT_READY,
        committed_offset=committed_offset,
        expires_at=expires_at,
        updated_at=now,
    )
    if not updated:
        session.refresh_from_db()
        return False
    session.status = FileTransferStatus.AGENT_READY
    session.committed_offset = committed_offset
    session.expires_at = expires_at
    return True


def _resume_file_upload(request, agent, data):
    session = get_object_or_404(
        FileTransferSession,
        session_id=data["session_id"],
        agent=agent,
        user=request.user,
        operation=FileTransferOperation.UPLOAD,
    )

    if session.expires_at <= djangotime.now():
        _expire_transfer_session(session, agent)
        return notify_error("Upload session has expired and cannot be resumed")

    if session.status not in _FILE_TRANSFER_RESUMABLE_STATUSES:
        return notify_error(
            f"Upload session cannot be resumed (status: {session.status})"
        )

    filename = (data.get("filename") or "").strip()
    if filename and filename != session.filename:
        return notify_error("filename does not match the session being resumed")
    raw_total = data.get("total_size")
    if raw_total is not None and int(raw_total) != session.total_size:
        return notify_error("total_size does not match the session being resumed")

    redis_committed = get_upload_ack(session.session_id)
    resume_offset = max(session.committed_offset, redis_committed or 0)

    prepare_payload = {
        "session_id": str(session.session_id),
        "destination_path": session.destination_path,
        "filename": session.filename,
        "total_size": str(session.total_size),
        "chunk_size": str(session.chunk_size),
        "conflict_policy": session.conflict_policy
        or FileTransferConflictPolicy.REPLACE,
        "resume": "true",
        "committed_offset": str(resume_offset),
    }
    response = send_nats_command(
        agent, "files_upload_prepare", prepare_payload, timeout=30
    )

    if _nats_agent_unreachable(response):
        return notify_retryable(f"{response.data}. Try again shortly.")
    if isinstance(response, Response):
        return response
    if not isinstance(response, dict):
        return notify_error("Invalid agent response")
    if response.get("status") != "ready":
        error_message = response.get("error") or "Agent failed to resume upload"
        return notify_error(str(error_message))

    try:
        committed_offset = int(response.get("committed_offset", resume_offset))
    except (TypeError, ValueError):
        return notify_error("Invalid committed_offset from agent")
    if committed_offset < 0 or committed_offset > session.total_size:
        return notify_error("Invalid committed_offset from agent")

    clear_upload_session_redis(session.session_id)

    if not _mark_session_resumed(session, committed_offset):
        # cancelled during the prepare
        send_nats_command(
            agent,
            "files_upload_abort",
            {"session_id": str(session.session_id)},
            timeout=_FILE_TRANSFER_AGENT_RELEASE_TIMEOUT,
        )
        return notify_error(
            f"Upload session cannot be resumed (status: {session.status})"
        )

    return Response(
        {
            "session_id": str(session.session_id),
            "status": session.status,
            "chunk_size": session.chunk_size,
            "committed_offset": session.committed_offset,
            "resumed": True,
        }
    )


class ListFiles(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def get(self, request, agent_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        path = (request.query_params.get("path") or "").strip()

        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(
                request.query_params.get("page_size", FILE_BROWSER_DEFAULT_PAGE_SIZE)
            )
        except ValueError:
            return notify_error("page and page_size must be integers")

        if page < 1 or page > FILE_BROWSER_MAX_PAGE:
            return notify_error(f"page must be between 1 and {FILE_BROWSER_MAX_PAGE}")
        if page_size < 1 or page_size > FILE_BROWSER_MAX_PAGE_SIZE:
            return notify_error(
                f"page_size must be between 1 and {FILE_BROWSER_MAX_PAGE_SIZE}"
            )

        if path:
            path, path_err = canonical_file_browser_path(path, agent.plat)
            if path_err:
                return notify_error(path_err)
        elif page != 1:
            return notify_error("path is required")

        name_filter, filter_err = sanitize_file_browser_name_filter(
            request.query_params.get("filter")
        )
        if filter_err:
            return notify_error(filter_err)

        payload = {
            "path": path,
            "page": str(page),
            "page_size": str(page_size),
        }
        if name_filter:
            payload["filter"] = name_filter
        response = send_nats_command(agent, "files_list", payload, timeout=30)
        if isinstance(response, Response):
            return response

        if not isinstance(response, dict):
            return notify_error("Invalid agent response")

        resolved_path = (response.get("path") or path or "").strip()
        if not resolved_path:
            return notify_error("Agent did not return a browsable path")

        items = normalize_file_browser_items(response.get("items", []))
        try:
            total = int(response.get("total", len(items)))
        except (TypeError, ValueError):
            total = len(items)

        return Response(
            {
                "path": resolved_path,
                "items": items,
                "has_more": bool(response.get("has_more", False)),
                "page": page,
                "page_size": page_size,
                "total": total,
            }
        )

    def delete(self, request, agent_id):
        return _delete_agent_files(request, agent_id)


class GetFileProperties(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def get(self, request, agent_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        path = (request.query_params.get("path") or "").strip()
        if not path:
            return notify_error("path is required")

        path, path_err = canonical_file_browser_path(path, agent.plat)
        if path_err:
            return notify_error(path_err)

        response = send_nats_command(
            agent,
            "files_properties",
            {
                "path": path,
                "max_files": str(FILE_BROWSER_PROPERTIES_MAX_FILES),
                "max_depth": str(FILE_BROWSER_PROPERTIES_MAX_DEPTH),
                "max_duration_seconds": str(
                    FILE_BROWSER_PROPERTIES_MAX_DURATION_SECONDS
                ),
            },
            timeout=45,
        )
        if isinstance(response, Response):
            return response

        if not isinstance(response, dict):
            return notify_error("Invalid agent response")

        item = normalize_file_browser_properties(response)
        if not item:
            return notify_error("Invalid agent response")

        return Response(item)


def _audit_file_browser(request, agent, action: str, operation: str, paths, extra=None):
    AuditLog.audit_file_browser_action(
        username=request.user.username,
        agent=agent,
        action=action,
        operation=operation,
        paths=list(paths),
        debug_info={"ip": getattr(request, "_client_ip", "")},
        extra=extra,
    )


def _log_transfer_terminal(session: FileTransferSession, detail: str = "") -> None:
    if session.status == FileTransferStatus.COMPLETED:
        # a complete won the race
        return
    message = detail or session.error_message or session.status
    log = (
        logger.info if session.status == FileTransferStatus.CANCELLED else logger.error
    )
    log(
        "file_transfer session=%s operation=%s status=%s: %s",
        session.session_id,
        session.operation,
        session.status,
        message,
    )


def _body_str(request, key: str):
    """Return ``(stripped value, None)`` for a string body field, or
    ``("", 400 response)`` when the body or the field has the wrong type."""
    if not isinstance(request.data, dict):
        return "", notify_error("Request body must be a JSON object")
    value = request.data.get(key)
    if value is None:
        return "", None
    if not isinstance(value, str):
        return "", notify_error(f"{key} must be a string")
    return value.strip(), None


class CheckFileExists(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        path, body_err = _body_str(request, "path")
        if body_err:
            return body_err
        if not path:
            return notify_error("path is required")

        path, path_err = canonical_file_browser_path(path, agent.plat)
        if path_err:
            return notify_error(path_err)

        raw_names = request.data.get("names")
        if not isinstance(raw_names, list):
            return notify_error("names must be a list")
        if len(raw_names) > FILE_BROWSER_MAX_EXISTS_NAMES:
            return notify_error(
                f"Select at most {FILE_BROWSER_MAX_EXISTS_NAMES} names to check"
            )

        names = []
        seen = set()
        for raw in raw_names:
            name_err = validate_file_browser_name(raw, field="names", plat=agent.plat)
            if name_err:
                return notify_error(name_err)
            name = str(raw).strip()
            key = name.lower() if agent.plat == "windows" else name
            if key in seen:
                continue
            seen.add(key)
            names.append(name)
        if not names:
            return notify_error("names must contain at least one name")

        response = send_nats_command(
            agent,
            "files_exists",
            {
                "path": path,
                "names_json": json.dumps(names),
            },
            timeout=30,
        )
        if isinstance(response, Response):
            return response
        if not isinstance(response, dict):
            return notify_error("Invalid agent response")
        if response.get("error"):
            return notify_error(str(response.get("error")))

        existing_raw = response.get("existing", [])
        existing = []
        if isinstance(existing_raw, list):
            existing = [str(item) for item in existing_raw if str(item).strip()]

        return Response({"existing": existing})


class CreateFileFolder(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        path, body_err = _body_str(request, "path")
        if body_err:
            return body_err
        raw_name = request.data.get("name")
        if not path:
            return notify_error("path is required")

        path, path_err = canonical_file_browser_path(path, agent.plat)
        if path_err:
            return notify_error(path_err)

        name_err = validate_file_browser_name(raw_name, field="name", plat=agent.plat)
        if name_err:
            return notify_error(name_err)

        name = str(raw_name).strip()

        response = send_nats_command(
            agent,
            "files_mkdir",
            {"path": path, "name": name},
            timeout=30,
            prefix_error=False,
        )
        if isinstance(response, Response):
            return response

        if not isinstance(response, dict):
            return notify_error("Invalid agent response")

        item = normalize_file_browser_item(response)
        if not item:
            return notify_error("Invalid agent response")

        _audit_file_browser(
            request,
            agent,
            AuditActionType.ADD,
            "mkdir",
            [item.get("path") or path],
            extra={"name": name, "parent": path},
        )
        return Response({"status": "success", "item": item})


class RenameFile(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        raw_path, body_err = _body_str(request, "path")
        if body_err:
            return body_err
        raw_new_name = request.data.get("new_name")
        if not raw_path:
            return notify_error("path is required")

        path, path_err = canonical_file_browser_path(raw_path, agent.plat)
        if path_err:
            return notify_error(path_err)

        name_err = validate_file_browser_name(
            raw_new_name, field="new_name", plat=agent.plat
        )
        if name_err:
            return notify_error(name_err)

        new_name = str(raw_new_name).strip()

        response = send_nats_command(
            agent,
            "files_rename",
            {"path": path, "new_name": new_name},
            timeout=30,
            prefix_error=False,
        )
        if isinstance(response, Response):
            return response

        if not isinstance(response, dict):
            return notify_error("Invalid agent response")

        item = normalize_file_browser_item(response)
        if not item:
            return notify_error("Invalid agent response")

        _audit_file_browser(
            request,
            agent,
            AuditActionType.MODIFY,
            "rename",
            [path],
            extra={"new_name": new_name, "item_path": item.get("path")},
        )
        return Response({"status": "success", "item": item})


def _delete_agent_files(request, agent_id):
    agent = get_validated_agent(agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION)
    if isinstance(agent, Response):
        return agent

    if not isinstance(request.data, dict):
        return notify_error("Request body must be a JSON object")
    paths = request.data.get("paths")
    normalized_paths, paths_err = canonical_file_browser_paths(paths, agent.plat)
    if paths_err:
        return notify_error(paths_err)
    response = send_nats_command(
        agent,
        "files_delete",
        {"paths": json.dumps(normalized_paths)},
        timeout=60,
    )
    if isinstance(response, Response):
        return response

    if not isinstance(response, dict):
        return notify_error("Invalid agent response")

    results = normalize_file_browser_delete_results(response.get("results", []))
    if not results:
        return notify_error("Invalid agent response")

    _audit_file_browser(
        request,
        agent,
        AuditActionType.DELETE,
        "delete",
        normalized_paths,
        extra={"results": results},
    )
    return Response({"status": "success", "results": results})


class InitFileUpload(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        serializer = InitFileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return notify_serializer_error(serializer)
        data = serializer.validated_data

        if data.get("session_id"):
            return _resume_file_upload(request, agent, data)

        filename = (data.get("filename") or "").strip()
        destination_path = (data.get("destination_path") or "").strip()

        filename_err = validate_file_transfer_filename(
            filename,
            ban_trailing_space_or_period=agent.plat == AgentPlat.WINDOWS,
            ban_windows_reserved=agent.plat == AgentPlat.WINDOWS,
        )
        if filename_err:
            return notify_error(filename_err)

        path_err = validate_file_transfer_destination_path(destination_path, agent.plat)
        if path_err:
            return notify_error(path_err)

        total_size = data.get("total_size")
        if total_size is None:
            return notify_error("total_size must be a positive integer")

        if (
            FILE_BROWSER_MAX_UPLOAD_FILE_SIZE_BYTES > 0
            and total_size > FILE_BROWSER_MAX_UPLOAD_FILE_SIZE_BYTES
        ):
            max_mib = FILE_BROWSER_MAX_UPLOAD_FILE_SIZE_BYTES // (1024 * 1024)
            return notify_error(
                f"File size exceeds the maximum allowed upload size ({max_mib} MiB)."
            )

        full_destination_path = resolve_upload_destination_path(
            destination_path, filename, agent.plat
        )
        path_err = validate_file_transfer_destination_path(
            full_destination_path, agent.plat
        )
        if path_err:
            return notify_error(path_err)

        chunk_size = _file_transfer_chunk_size(data.get("chunk_size"))

        conflict_policy = _normalize_upload_conflict_policy(data.get("conflict_policy"))
        if conflict_policy is None:
            return notify_error("conflict_policy must be 'replace' or 'skip'")

        session = create_file_transfer_session_locked(
            agent,
            request.user,
            operation=FileTransferOperation.UPLOAD,
            status=FileTransferStatus.WAITING_FOR_AGENT,
            destination_path=full_destination_path,
            filename=filename,
            conflict_policy=conflict_policy,
            total_size=total_size,
            chunk_size=chunk_size,
            committed_offset=0,
            expires_at=djangotime.now()
            + dt.timedelta(hours=FILE_TRANSFER_SESSION_TTL_HOURS),
        )
        if isinstance(session, Response):
            return session

        prepare_payload = {
            "session_id": str(session.session_id),
            "destination_path": session.destination_path,
            "filename": session.filename,
            "total_size": str(session.total_size),
            "chunk_size": str(session.chunk_size),
            "conflict_policy": session.conflict_policy,
        }
        response = send_nats_command(
            agent, "files_upload_prepare", prepare_payload, timeout=30
        )

        if isinstance(response, Response):
            _fail_transfer_session(session, agent, str(response.data))
            return response

        if not isinstance(response, dict):
            _fail_transfer_session(session, agent, "Invalid agent response")
            return notify_error("Invalid agent response")

        if response.get("status") != "ready":
            error_message = response.get("error") or "Agent failed to prepare upload"
            _fail_transfer_session(session, agent, str(error_message))
            return notify_error(str(error_message))

        try:
            committed_offset = int(response.get("committed_offset", 0))
        except (TypeError, ValueError):
            _fail_transfer_session(
                session, agent, "Invalid committed_offset from agent"
            )
            return notify_error("Invalid committed_offset from agent")

        if committed_offset < 0 or committed_offset > session.total_size:
            _fail_transfer_session(
                session, agent, "Invalid committed_offset from agent"
            )
            return notify_error("Invalid committed_offset from agent")

        session.status = FileTransferStatus.AGENT_READY
        session.committed_offset = committed_offset
        session.save(update_fields=["status", "committed_offset", "updated_at"])

        _audit_file_browser(
            request,
            agent,
            AuditActionType.FILE_TRANSFER,
            "upload",
            [session.destination_path],
            extra={
                "session_id": str(session.session_id),
                "filename": session.filename,
                "total_size": session.total_size,
            },
        )
        return Response(
            {
                "session_id": str(session.session_id),
                "status": session.status,
                "chunk_size": session.chunk_size,
                "committed_offset": session.committed_offset,
            }
        )


_FILE_TRANSFER_CHUNK_ACTIVE_STATUSES = (
    FileTransferStatus.AGENT_READY,
    FileTransferStatus.TRANSFERRING,
)
_FILE_TRANSFER_CHUNK_TERMINAL_STATUSES = (
    FileTransferStatus.COMPLETED,
    FileTransferStatus.FAILED,
    FileTransferStatus.CANCELLED,
    FileTransferStatus.EXPIRED,
)


def _upload_relay_put_state(session):
    """Return committed and accepted."""
    redis_committed = get_upload_ack(session.session_id)
    committed = max(session.committed_offset, redis_committed or 0)
    redis_accepted = get_accepted_offset(session.session_id)
    accepted = max(redis_accepted or 0, committed)
    depth_bytes = FILE_TRANSFER_PIPELINE_DEPTH * session.chunk_size
    can_put = (
        session.status in _FILE_TRANSFER_CHUNK_ACTIVE_STATUSES
        and accepted < session.total_size
        and not pipeline_depth_full(accepted, committed, depth_bytes)
    )
    return committed, accepted, can_put


def _upload_chunk_ready_payload(session, committed, accepted, can_put):
    return {
        "session_id": str(session.session_id),
        "status": session.status,
        "accepted_offset": accepted,
        "committed_offset": committed,
        "chunk_size": session.chunk_size,
        "total_size": session.total_size,
        "can_put": can_put,
        "error": session.error_message,
    }


class UploadFileChunk(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def get(self, request, agent_id, session_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.UPLOAD,
        )

        if session.expires_at <= djangotime.now():
            _expire_transfer_session(session, agent)
            return notify_error("Upload session has expired")

        if session.status in _FILE_TRANSFER_CHUNK_TERMINAL_STATUSES:
            committed, accepted, _can_put = _upload_relay_put_state(session)
            return Response(
                _upload_chunk_ready_payload(session, committed, accepted, False)
            )

        if session.status not in _FILE_TRANSFER_CHUNK_ACTIVE_STATUSES:
            return notify_error("Upload session is not ready to receive chunks")

        committed, accepted, can_put = _upload_relay_put_state(session)
        return Response(
            _upload_chunk_ready_payload(session, committed, accepted, can_put)
        )

    def put(self, request, agent_id, session_id):
        """Accept one chunk from the client.

        Pipeline-depth protocol:
          - Django accepts up to FILE_TRANSFER_PIPELINE_DEPTH chunks ahead of
            what the agent has committed (same cap as download).
          - The PUT returns immediately once the chunk is stored in Redis and
            NATS-notified. The client does not wait for the agent to write.
          - If the pipeline is full, poll GET on this URL until can_put;
            the PUT itself stays retryable for a race.

        Response fields:
          accepted_offset  — client should start the next chunk here
          committed_offset — last offset confirmed written by the agent
          can_put          — the next chunk fits in the pipeline now; when
                             false, poll GET before sending it
        """
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.UPLOAD,
        )

        if session.expires_at <= djangotime.now():
            _expire_transfer_session(session, agent)
            return notify_error("Upload session has expired")

        if session.status == FileTransferStatus.FAILED:
            return notify_error(session.error_message or "Upload failed")
        if session.status not in _FILE_TRANSFER_CHUNK_ACTIVE_STATUSES:
            return notify_error("Upload session is not ready to receive chunks")

        content_range = request.META.get("HTTP_CONTENT_RANGE", "")
        byte_range, range_err = parse_upload_content_range(
            content_range, session.total_size
        )
        if range_err:
            return notify_error(range_err)

        start, end = byte_range
        expected_len = end - start + 1

        if expected_len < 1 or expected_len > session.chunk_size:
            return notify_error("Chunk size exceeds allowed limit")

        content_length = request.META.get("CONTENT_LENGTH")
        if content_length:
            try:
                if int(content_length) != expected_len:
                    return notify_error(
                        "Request body size does not match Content-Range"
                    )
            except ValueError:
                return notify_error("Invalid Content-Length header")

        if expected_len > FILE_TRANSFER_CHUNK_SIZE_MAX:
            return notify_error("Chunk exceeds maximum request size")

        committed, accepted, can_put = _upload_relay_put_state(session)

        if start < accepted:
            return Response(
                {
                    "session_id": str(session.session_id),
                    "status": session.status,
                    "accepted_offset": accepted,
                    "committed_offset": committed,
                    "chunk_start": start,
                    "chunk_end": end,
                    "chunk_bytes": expected_len,
                    "can_put": can_put,
                }
            )

        if start != accepted:
            return notify_error(
                f"Chunk start offset {start} does not match expected {accepted}"
            )

        if not can_put:
            committed, accepted, can_put = _upload_relay_put_state(session)
            if start < accepted:
                return Response(
                    {
                        "session_id": str(session.session_id),
                        "status": session.status,
                        "accepted_offset": accepted,
                        "committed_offset": committed,
                        "chunk_start": start,
                        "chunk_end": end,
                        "chunk_bytes": expected_len,
                        "can_put": can_put,
                    }
                )
            if not can_put:
                session.refresh_from_db(fields=["status", "error_message"])
                if session.status == FileTransferStatus.FAILED:
                    clear_upload_session_redis(session.session_id)
                    return notify_error(session.error_message or "Upload failed")
                _ = request.body
                return notify_retryable(
                    "Timed out waiting for agent to commit previous chunk"
                )

        chunk_data = request.body
        if len(chunk_data) != expected_len:
            return notify_error("Request body size does not match Content-Range")

        store_err = store_upload_chunk(session.session_id, start, end, chunk_data)
        if store_err:
            return notify_error(store_err)

        if not _mark_transfer_transferring(session):
            # cancelled or failed while the chunk was being stored
            clear_upload_session_redis(session.session_id)
            if session.status == FileTransferStatus.FAILED:
                return notify_error(session.error_message or "Upload failed")
            return notify_error("Upload session is not ready to receive chunks")

        notify_payload = {
            "session_id": str(session.session_id),
            "chunk_start": str(start),
            "chunk_end": str(end),
            "chunk_size": str(len(chunk_data)),
        }
        notify_err = send_nats_notification(
            agent, "files_upload_chunk_available", notify_payload
        )

        if notify_err is not None:
            # nats is probably restarting, let the client resend the chunk
            rollback_upload_chunk(session.session_id, start, prev_accepted=start)
            logger.warning(
                "file_transfer upload chunk notify failed session=%s start=%s: %s",
                session.session_id,
                start,
                notify_err.data,
            )
            return notify_retryable(f"{notify_err.data}. Retrying.")

        accepted_offset = end + 1
        # Tell the client whether the next chunk fits so it only polls the
        # ready GET when the pipeline is actually full.
        committed, _accepted, next_can_put = _upload_relay_put_state(session)
        logger.info(
            "file_transfer upload chunk accepted session=%s start=%s end=%s",
            session.session_id,
            start,
            end,
        )

        return Response(
            {
                "session_id": str(session.session_id),
                "status": session.status,
                "accepted_offset": accepted_offset,
                "committed_offset": committed,
                "chunk_start": start,
                "chunk_end": end,
                "chunk_bytes": len(chunk_data),
                "can_put": next_can_put,
            }
        )


class CompleteFileUpload(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id, session_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.UPLOAD,
        )

        if session.expires_at <= djangotime.now():
            _expire_transfer_session(session, agent)
            return notify_error("Upload session has expired")

        if session.status == FileTransferStatus.COMPLETED:
            client_sha256, body_err = _body_str(request, "sha256")
            if body_err:
                return body_err
            return Response(_upload_complete_body(session, client_sha256.lower()))

        if session.status not in (
            FileTransferStatus.AGENT_READY,
            FileTransferStatus.TRANSFERRING,
        ):
            return notify_error("Upload session is not ready to complete")

        redis_committed = get_upload_ack(session.session_id)
        committed_offset = max(session.committed_offset, redis_committed or 0)

        if committed_offset < session.total_size:
            redis_committed = get_upload_ack(session.session_id)
            committed_offset = max(committed_offset, redis_committed or 0)
            if committed_offset < session.total_size:
                session.refresh_from_db(fields=["status", "error_message"])
                if session.status == FileTransferStatus.FAILED:
                    return notify_error(session.error_message or "Upload failed")
                return notify_retryable(
                    "Timed out waiting for agent to commit final chunk"
                )

        if session.committed_offset != committed_offset:
            session.committed_offset = committed_offset
            session.last_ack_at = djangotime.now()
            session.save(
                update_fields=[
                    "committed_offset",
                    "last_ack_at",
                    "updated_at",
                ]
            )

        finalize_payload = {
            "session_id": str(session.session_id),
            "destination_path": session.destination_path,
            "total_size": str(session.total_size),
            "conflict_policy": session.conflict_policy
            or FileTransferConflictPolicy.REPLACE,
        }

        client_sha256, body_err = _body_str(request, "sha256")
        if body_err:
            return body_err
        client_sha256 = client_sha256.lower()
        if client_sha256:
            finalize_payload["sha256"] = client_sha256
        response = send_nats_command(
            agent, "files_upload_finalize", finalize_payload, timeout=30
        )

        if not _nats_finalize_succeeded(response):
            return _upload_finalize_failure_response(
                session, agent, response, client_sha256
            )

        clear_upload_session_redis(session.session_id)
        session = _mark_transfer_completed(session)
        if session.status != FileTransferStatus.COMPLETED:
            return notify_error("Upload session is not ready to complete")

        return Response(
            _upload_complete_body(session, response.get("sha256") or client_sha256)
        )


def _resume_file_download(request, agent, data):
    session = get_object_or_404(
        FileTransferSession,
        session_id=data["session_id"],
        agent=agent,
        user=request.user,
        operation=FileTransferOperation.DOWNLOAD,
    )

    if session.expires_at <= djangotime.now():
        _expire_transfer_session(session, agent)
        return notify_error("Download session has expired and cannot be resumed")

    if session.status not in _FILE_TRANSFER_RESUMABLE_STATUSES:
        return notify_error(
            f"Download session cannot be resumed (status: {session.status})"
        )

    if session.is_archive and session.status not in (
        FileTransferStatus.AGENT_READY,
        FileTransferStatus.TRANSFERRING,
    ):
        return notify_error("Archive is still being prepared; cannot resume yet")

    resume_offset = data.get("resume_offset")
    if resume_offset is None:
        resume_offset = session.committed_offset

    if resume_offset < 0 or resume_offset > session.total_size:
        return notify_error("resume_offset is out of range")
    if resume_offset % session.chunk_size != 0 and resume_offset != session.total_size:
        return notify_error("resume_offset must be aligned to chunk_size")

    prepare_payload = {
        "session_id": str(session.session_id),
        "source_path": session.destination_path,
        "chunk_size": str(session.chunk_size),
        "resume": "true",
        "committed_offset": str(resume_offset),
    }
    if session.is_archive:
        prepare_payload["remove_on_close"] = "true"

    clear_download_session_redis(session.session_id)

    response = send_nats_command(
        agent, "files_download_prepare", prepare_payload, timeout=30
    )

    if _nats_agent_unreachable(response):
        return notify_retryable(f"{response.data}. Try again shortly.")
    if isinstance(response, Response):
        return response
    if not isinstance(response, dict):
        return notify_error("Invalid agent response")
    if response.get("status") != "ready":
        error_message = response.get("error") or "Agent failed to resume download"
        return notify_error(str(error_message))

    try:
        total_size = int(response.get("total_size", 0))
    except (TypeError, ValueError):
        return notify_error("Invalid total_size from agent")

    if total_size != session.total_size:
        return notify_error(
            "Source file changed since the transfer started; cannot resume"
        )

    if not _mark_session_resumed(session, resume_offset):
        # cancelled during the prepare
        clear_download_session_redis(session.session_id)
        send_nats_command(
            agent,
            "files_download_finalize",
            {
                "session_id": str(session.session_id),
                "source_path": session.destination_path,
                "release": "true",
            },
            timeout=_FILE_TRANSFER_AGENT_RELEASE_TIMEOUT,
        )
        return notify_error(
            f"Download session cannot be resumed (status: {session.status})"
        )

    return Response(
        {
            "session_id": str(session.session_id),
            "status": session.status,
            "total_size": total_size,
            "chunk_size": session.chunk_size,
            "committed_offset": resume_offset,
            "resumed": True,
        }
    )


class InitFileDownload(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        serializer = InitFileDownloadSerializer(data=request.data)
        if not serializer.is_valid():
            return notify_serializer_error(serializer)
        data = serializer.validated_data

        if data.get("session_id"):
            return _resume_file_download(request, agent, data)

        source_path = (data.get("source_path") or "").strip()
        path_err = validate_file_transfer_source_path(source_path, agent.plat)
        if path_err:
            return notify_error(path_err)

        filename = source_path.split("/")[-1].split("\\")[-1] or "download"
        filename_err = validate_file_transfer_filename(
            filename, ban_trailing_space_or_period=False
        )
        if filename_err:
            return notify_error(filename_err)

        chunk_size = _file_transfer_chunk_size(data.get("chunk_size"))

        session = create_file_transfer_session_locked(
            agent,
            request.user,
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.WAITING_FOR_AGENT,
            destination_path=source_path,
            filename=filename,
            total_size=0,
            chunk_size=chunk_size,
            committed_offset=0,
            expires_at=djangotime.now()
            + dt.timedelta(hours=FILE_TRANSFER_SESSION_TTL_HOURS),
        )
        if isinstance(session, Response):
            return session

        prepare_payload = {
            "session_id": str(session.session_id),
            "source_path": source_path,
            "chunk_size": str(chunk_size),
        }
        response = send_nats_command(
            agent, "files_download_prepare", prepare_payload, timeout=30
        )

        if isinstance(response, Response):
            _fail_transfer_session(session, agent, str(response.data))
            return response

        if not isinstance(response, dict):
            _fail_transfer_session(session, agent, "Invalid agent response")
            return notify_error("Invalid agent response")

        if response.get("status") != "ready":
            error_message = response.get("error") or "Agent failed to prepare download"
            _fail_transfer_session(session, agent, str(error_message))
            return notify_error(str(error_message))

        try:
            total_size = int(response.get("total_size", 0))
        except (TypeError, ValueError):
            _fail_transfer_session(session, agent, "Invalid total_size from agent")
            return notify_error("Invalid total_size from agent")

        if total_size < 1:
            _fail_transfer_session(
                session, agent, "Agent reported empty or invalid file"
            )
            return notify_error("Agent reported empty or invalid file")

        # The agent's stream may already have reported a failure (or the
        # user cancelled) while the prepare call was in flight; do not put a
        # terminal row back to agent_ready with no stream behind it.
        updated = FileTransferSession.objects.filter(
            pk=session.pk, status=FileTransferStatus.WAITING_FOR_AGENT
        ).update(
            total_size=total_size,
            status=FileTransferStatus.AGENT_READY,
            updated_at=djangotime.now(),
        )
        if not updated:
            session.refresh_from_db(fields=["status", "error_message"])
            return notify_error(
                session.error_message
                or f"Download session is no longer active (status: {session.status})"
            )
        session.total_size = total_size
        session.status = FileTransferStatus.AGENT_READY

        _audit_file_browser(
            request,
            agent,
            AuditActionType.FILE_TRANSFER,
            "download",
            [source_path],
            extra={
                "session_id": str(session.session_id),
                "filename": session.filename,
                "total_size": total_size,
            },
        )
        return Response(
            {
                "session_id": str(session.session_id),
                "status": session.status,
                "total_size": total_size,
                "chunk_size": chunk_size,
                "committed_offset": 0,
            }
        )


class InitFileDownloadArchive(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        serializer = InitFileDownloadArchiveSerializer(data=request.data)
        if not serializer.is_valid():
            return notify_serializer_error(serializer)
        data = serializer.validated_data

        raw_paths = data.get("paths")
        validated_paths, paths_err = collect_file_transfer_paths(
            raw_paths,
            agent.plat,
            max_paths=FILE_BROWSER_MAX_ARCHIVE_PATHS,
            max_exceeded_message=(
                f"Select at most {FILE_BROWSER_MAX_ARCHIVE_PATHS} paths for archive download"
            ),
        )
        if paths_err:
            return notify_error(paths_err)
        assert validated_paths is not None

        filename = derive_archive_download_filename(
            validated_paths, data.get("filename")
        )
        filename_err = validate_file_transfer_filename(filename)
        if filename_err:
            return notify_error(filename_err)

        chunk_size = _file_transfer_chunk_size(data.get("chunk_size"))

        session = create_file_transfer_session_locked(
            agent,
            request.user,
            operation=FileTransferOperation.DOWNLOAD,
            status=FileTransferStatus.WAITING_FOR_AGENT,
            destination_path=validated_paths[0],
            filename=filename,
            total_size=0,
            chunk_size=chunk_size,
            committed_offset=0,
            is_archive=True,
            expires_at=djangotime.now()
            + dt.timedelta(minutes=FILE_BROWSER_ARCHIVE_BUILD_TTL_MINUTES),
        )
        if isinstance(session, Response):
            return session

        prepare_payload = {
            "session_id": str(session.session_id),
            "paths_json": json.dumps(validated_paths),
            "chunk_size": str(chunk_size),
            "max_files": str(FILE_BROWSER_MAX_ARCHIVE_FILES),
            "max_size_bytes": str(FILE_BROWSER_MAX_ARCHIVE_SIZE_BYTES),
            "max_depth": str(FILE_BROWSER_MAX_ARCHIVE_DEPTH),
        }

        logger.info(
            "file_transfer archive download init session=%s agent=%s user=%s paths=%d filename=%s",
            session.session_id,
            agent.agent_id,
            request.user.pk,
            len(validated_paths),
            filename,
        )

        response = send_nats_command(
            agent,
            "files_download_archive_prepare",
            prepare_payload,
            timeout=30,
        )

        if isinstance(response, Response):
            _fail_transfer_session(session, agent, str(response.data))
            return response

        if not isinstance(response, dict):
            _fail_transfer_session(session, agent, "Invalid agent response")
            return notify_error("Invalid agent response")

        if response.get("status") != "building":
            error_message = (
                response.get("error") or "Agent failed to start archive build"
            )
            _fail_transfer_session(session, agent, str(error_message))
            return notify_error(str(error_message))

        _audit_file_browser(
            request,
            agent,
            AuditActionType.FILE_TRANSFER,
            "archive_download",
            validated_paths,
            extra={
                "session_id": str(session.session_id),
                "filename": filename,
            },
        )
        return Response(
            {
                "session_id": str(session.session_id),
                "status": session.status,
                "total_size": 0,
                "chunk_size": chunk_size,
                "committed_offset": 0,
                "filename": filename,
                "is_archive": True,
                "preparing": True,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class GetFileDownloadChunk(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def get(self, request, agent_id, session_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.DOWNLOAD,
        )

        if session.expires_at <= djangotime.now():
            _expire_transfer_session(session, agent)
            return notify_error("Download session has expired")

        if session.status not in (
            FileTransferStatus.AGENT_READY,
            FileTransferStatus.TRANSFERRING,
        ):
            return notify_error("Download session is not ready to serve chunks")

        try:
            client_committed = int(request.query_params.get("committed_offset", 0))
        except (TypeError, ValueError):
            client_committed = 0
        redis_committed = get_download_ack(session.session_id)
        committed = max(
            session.committed_offset, redis_committed or 0, client_committed
        )

        # No chunk yet is the normal state while the agent pushes; answer
        # 204 (poll again) rather than an error status the browser logs.
        offered = get_download_offered_offset(session.session_id)
        if offered is None or offered <= committed:
            session.refresh_from_db(fields=["status", "error_message"])
            if session.status == FileTransferStatus.FAILED:
                return notify_error(session.error_message or "Download failed")
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)

        chunk = peek_download_chunk(session.session_id, committed)
        if chunk is None:
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)

        logger.info(
            "file_transfer download chunk served session=%s start=%s end=%s",
            session.session_id,
            chunk.start,
            chunk.end,
        )

        response = HttpResponse(chunk.data, content_type="application/octet-stream")
        response["Content-Range"] = (
            f"bytes {chunk.start}-{chunk.end}/{session.total_size}"
        )
        response["X-Chunk-Start"] = str(chunk.start)
        response["X-Chunk-End"] = str(chunk.end)
        return response


class AckFileDownloadChunk(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id, session_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.DOWNLOAD,
        )

        if session.expires_at <= djangotime.now():
            _expire_transfer_session(session, agent)
            return notify_error("Download session has expired")

        if session.status not in (
            FileTransferStatus.AGENT_READY,
            FileTransferStatus.TRANSFERRING,
        ):
            return notify_error("Download session is not ready for ACK")

        try:
            committed_offset = int(request.data.get("committed_offset"))
        except (AttributeError, TypeError, ValueError):
            return notify_error("committed_offset must be a positive integer")

        if committed_offset < 1 or committed_offset > session.total_size:
            return notify_error("committed_offset is out of range")

        redis_committed = get_download_ack(session.session_id)
        current_committed = max(session.committed_offset, redis_committed or 0)

        if committed_offset < current_committed:
            return notify_error("committed_offset cannot decrease")

        redis_offered = get_download_offered_offset(session.session_id)
        if redis_offered is not None and committed_offset > redis_offered:
            return notify_error("committed_offset exceeds offered_offset")

        should_checkpoint = (
            committed_offset == session.total_size
            or committed_offset - session.committed_offset
            >= FILE_TRANSFER_ACK_CHECKPOINT_BYTES
        )
        if should_checkpoint:
            now = djangotime.now()
            update_fields = [
                "committed_offset",
                "last_ack_at",
                "expires_at",
                "updated_at",
            ]
            session.committed_offset = committed_offset
            session.last_ack_at = now
            session.expires_at = now + dt.timedelta(
                hours=FILE_TRANSFER_SESSION_TTL_HOURS
            )
            session.save(update_fields=update_fields)
            _mark_transfer_transferring(session)

        if committed_offset > current_committed:
            delete_download_chunk(session.session_id, current_committed)

        signal_download_ack(session.session_id, committed_offset)

        notify_err = send_nats_notification(
            agent,
            "files_download_ack",
            {
                "session_id": str(session.session_id),
                "committed_offset": str(committed_offset),
            },
        )
        if notify_err is not None:
            logger.warning(
                "file_transfer download ack nats notify failed session=%s: %s",
                session.session_id,
                notify_err.data,
            )

        return Response({"committed_offset": committed_offset})


class CompleteFileDownload(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id, session_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.DOWNLOAD,
        )

        if session.expires_at <= djangotime.now():
            _expire_transfer_session(session, agent)
            return notify_error("Download session has expired")

        if session.status == FileTransferStatus.COMPLETED:
            return Response(_download_complete_body(session, ""))

        if session.status not in (
            FileTransferStatus.AGENT_READY,
            FileTransferStatus.TRANSFERRING,
        ):
            return notify_error("Download session is not ready to complete")

        redis_committed = get_download_ack(session.session_id)
        committed_offset = max(session.committed_offset, redis_committed or 0)

        if committed_offset < session.total_size:
            session.refresh_from_db(fields=["status", "error_message"])
            if session.status == FileTransferStatus.FAILED:
                return notify_error(session.error_message or "Download failed")
            return notify_retryable("Timed out waiting for client to ACK all chunks")

        if session.committed_offset != committed_offset:
            session.committed_offset = committed_offset
            session.last_ack_at = djangotime.now()
            session.save(
                update_fields=[
                    "committed_offset",
                    "last_ack_at",
                    "updated_at",
                ]
            )

        finalize_payload = {
            "session_id": str(session.session_id),
            "source_path": session.destination_path,
        }
        response = send_nats_command(
            agent, "files_download_finalize", finalize_payload, timeout=30
        )

        if not _nats_finalize_succeeded(response):
            return _download_finalize_failure_response(session, agent, response)

        clear_download_session_redis(session.session_id)
        session = _mark_transfer_completed(session)
        if session.status != FileTransferStatus.COMPLETED:
            return notify_error("Download session is not ready to complete")

        return Response(_download_complete_body(session, response.get("sha256", "")))


_FILE_TRANSFER_AGENT_RELEASE_TIMEOUT = 5
_FILE_TRANSFER_RELEASED_STATUSES = (
    FileTransferStatus.COMPLETED,
    FileTransferStatus.CANCELLED,
)


def _upload_complete_body(session: FileTransferSession, sha256: str) -> dict:
    return {
        "session_id": str(session.session_id),
        "status": session.status,
        "destination_path": session.destination_path,
        "committed_offset": session.committed_offset,
        "sha256": sha256 or "",
    }


def _download_complete_body(session: FileTransferSession, sha256: str) -> dict:
    return {
        "session_id": str(session.session_id),
        "status": session.status,
        "source_path": session.destination_path,
        "committed_offset": session.committed_offset,
        "sha256": sha256 or "",
    }


def _nats_finalize_succeeded(response) -> bool:
    return isinstance(response, dict) and response.get("status") == "completed"


def _nats_finalize_error(response, fallback: str) -> str:
    if isinstance(response, Response):
        data = response.data
        if isinstance(data, str) and data.strip():
            return data.strip()[:2048]
        return str(data)[:2048]
    if isinstance(response, dict):
        return str(response.get("error") or fallback)[:2048]
    return "Invalid agent response"


def _nats_agent_unreachable(response) -> bool:
    if not isinstance(response, Response):
        return False
    detail = str(response.data)
    return detail == NATS_UNAVAILABLE_MESSAGE or detail.startswith(NATS_FAILED_PREFIX)


def _session_completed_during_nats(session: FileTransferSession) -> bool:
    session.refresh_from_db()
    return session.status == FileTransferStatus.COMPLETED


def _mark_transfer_completed(session: FileTransferSession) -> FileTransferSession:
    with transaction.atomic():
        locked = (
            FileTransferSession.objects.select_for_update()
            .filter(pk=session.pk)
            .first()
        )
        if locked is None:
            return session
        if locked.status == FileTransferStatus.CANCELLED:
            return locked
        locked.status = FileTransferStatus.COMPLETED
        locked.error_message = ""
        locked.save(update_fields=["status", "error_message", "updated_at"])
        return locked


def _mark_transfer_transferring(session: FileTransferSession) -> bool:
    """Conditional update so we don't overwrite a cancel. Returns False if the
    session is no longer active."""
    if session.status != FileTransferStatus.AGENT_READY:
        session.refresh_from_db(fields=["status", "error_message"])
        return session.status in _FILE_TRANSFER_CHUNK_ACTIVE_STATUSES
    updated = FileTransferSession.objects.filter(
        pk=session.pk, status=FileTransferStatus.AGENT_READY
    ).update(status=FileTransferStatus.TRANSFERRING, updated_at=djangotime.now())
    if updated:
        session.status = FileTransferStatus.TRANSFERRING
        return True
    session.refresh_from_db(fields=["status", "error_message"])
    return session.status in _FILE_TRANSFER_CHUNK_ACTIVE_STATUSES


def _apply_transfer_terminal_status(
    session: FileTransferSession,
    new_status: str,
    error_message: str,
) -> bool:
    with transaction.atomic():
        locked = (
            FileTransferSession.objects.select_for_update()
            .filter(pk=session.pk)
            .first()
        )
        if locked is None:
            return False
        if locked.status in _FILE_TRANSFER_RELEASED_STATUSES:
            session.status = locked.status
            session.error_message = locked.error_message
            session.committed_offset = locked.committed_offset
            session.destination_path = locked.destination_path
            return False
        locked.status = new_status
        locked.error_message = error_message
        locked.save(update_fields=["status", "error_message", "updated_at"])
        session.status = locked.status
        session.error_message = locked.error_message
        return True


def _upload_finalize_failure_response(
    session: FileTransferSession,
    agent,
    response,
    client_sha256: str,
):
    if _session_completed_during_nats(session):
        return Response(_upload_complete_body(session, client_sha256))
    if _nats_agent_unreachable(response):
        return notify_retryable("Timed out waiting for agent to finalize upload")
    fail_message = _nats_finalize_error(response, "Agent failed to finalize upload")
    _fail_transfer_session(session, agent, fail_message)
    if session.status == FileTransferStatus.COMPLETED:
        return Response(_upload_complete_body(session, client_sha256))
    if isinstance(response, Response):
        return response
    return notify_error(fail_message)


def _download_finalize_failure_response(session: FileTransferSession, agent, response):
    if _session_completed_during_nats(session):
        return Response(_download_complete_body(session, ""))
    if _nats_agent_unreachable(response):
        return notify_retryable("Timed out waiting for agent to finalize download")
    fail_message = _nats_finalize_error(response, "Agent failed to finalize download")
    _fail_transfer_session(session, agent, fail_message)
    if session.status == FileTransferStatus.COMPLETED:
        return Response(_download_complete_body(session, ""))
    if isinstance(response, Response):
        return response
    return notify_error(fail_message)


def _release_download_session(
    session: FileTransferSession,
    agent,
    error_message: str = "Download cancelled",
    new_status: str = FileTransferStatus.FAILED,
) -> None:
    session.refresh_from_db()
    if session.status in _FILE_TRANSFER_RELEASED_STATUSES:
        return

    # set the status before clearing redis so the agent can't push into a
    # session with no offsets
    applied = _apply_transfer_terminal_status(session, new_status, error_message)
    clear_download_session_redis(session.session_id)
    if agent is not None and agent.status == AGENT_STATUS_ONLINE:
        finalize_payload = {
            "session_id": str(session.session_id),
            "source_path": session.destination_path,
            "release": "true",
        }
        response = send_nats_command(
            agent,
            "files_download_finalize",
            finalize_payload,
            timeout=_FILE_TRANSFER_AGENT_RELEASE_TIMEOUT,
        )
        if isinstance(response, dict) and response.get("error"):
            logger.warning(
                "file_transfer download release session=%s agent finalize: %s",
                session.session_id,
                response.get("error"),
            )
    # again, in case a chunk was stored during the release
    clear_download_session_redis(session.session_id)
    # a complete may have won the race
    session.refresh_from_db(fields=["status", "error_message"])
    if applied:
        _log_transfer_terminal(session, error_message)


def _release_upload_session(
    session: FileTransferSession,
    agent,
    error_message: str = "Upload cancelled",
    new_status: str = FileTransferStatus.FAILED,
) -> None:
    session.refresh_from_db()
    if session.status in _FILE_TRANSFER_RELEASED_STATUSES:
        return

    # set the status before clearing redis so the agent can't push into a
    # session with no offsets
    applied = _apply_transfer_terminal_status(session, new_status, error_message)
    clear_upload_session_redis(session.session_id)
    if agent is not None and agent.status == AGENT_STATUS_ONLINE:
        abort_payload = {"session_id": str(session.session_id)}
        response = send_nats_command(
            agent,
            "files_upload_abort",
            abort_payload,
            timeout=_FILE_TRANSFER_AGENT_RELEASE_TIMEOUT,
        )
        if isinstance(response, dict) and response.get("error"):
            logger.warning(
                "file_transfer upload release session=%s agent abort: %s",
                session.session_id,
                response.get("error"),
            )
    # again, in case a chunk was stored during the release
    clear_upload_session_redis(session.session_id)
    # a complete may have won the race
    session.refresh_from_db(fields=["status", "error_message"])
    if applied:
        _log_transfer_terminal(session, error_message)


def _release_extract_session(
    session: FileTransferSession,
    agent,
    error_message: str = "Extract cancelled",
    new_status: str = FileTransferStatus.FAILED,
) -> None:
    applied = FileTransferSession.objects.filter(
        pk=session.pk, status__in=_FILE_TRANSFER_ACTIVE_STATUSES
    ).update(
        status=new_status, error_message=error_message, updated_at=djangotime.now()
    )
    if not applied:
        session.refresh_from_db()
        return
    if agent is not None and agent.status == AGENT_STATUS_ONLINE:
        response = send_nats_command(
            agent,
            "files_extract_cancel",
            {"session_id": str(session.session_id)},
            timeout=_FILE_TRANSFER_AGENT_RELEASE_TIMEOUT,
        )
        if isinstance(response, dict) and response.get("error"):
            logger.warning(
                "file_transfer extract release session=%s agent cancel: %s",
                session.session_id,
                response.get("error"),
            )
        elif isinstance(response, dict) and "files" in response:
            FileTransferSession.objects.filter(pk=session.pk).update(
                files_done=_non_negative_int(response.get("files")),
                files_skipped=_non_negative_int(response.get("skipped")),
            )
    session.refresh_from_db()
    _log_transfer_terminal(session, error_message)


def _non_negative_int(value) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _fail_transfer_session(
    session: FileTransferSession,
    agent,
    error_message: str,
) -> None:
    message = (error_message or "Transfer failed")[:2048]
    if session.operation == FileTransferOperation.EXTRACT:
        _release_extract_session(
            session,
            agent,
            error_message=message,
            new_status=FileTransferStatus.FAILED,
        )
        return
    if session.operation == FileTransferOperation.UPLOAD:
        _release_upload_session(
            session,
            agent,
            error_message=message,
            new_status=FileTransferStatus.FAILED,
        )
        return
    _release_download_session(
        session,
        agent,
        error_message=message,
        new_status=FileTransferStatus.FAILED,
    )


def _expire_transfer_session(session: FileTransferSession, agent) -> None:
    message = session.error_message or "Session expired"
    if session.operation == FileTransferOperation.EXTRACT:
        _release_extract_session(
            session,
            agent,
            error_message=session.error_message or EXTRACT_EXPIRED_MESSAGE,
            new_status=FileTransferStatus.EXPIRED,
        )
        return
    if session.operation == FileTransferOperation.UPLOAD:
        _release_upload_session(
            session,
            agent,
            error_message=message,
            new_status=FileTransferStatus.EXPIRED,
        )
        return
    _release_download_session(
        session,
        agent,
        error_message=message,
        new_status=FileTransferStatus.EXPIRED,
    )


class CancelFileDownload(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id, session_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.DOWNLOAD,
        )

        if session.status in _FILE_TRANSFER_RELEASED_STATUSES:
            return Response(
                {"session_id": str(session.session_id), "status": session.status}
            )

        if session.status in (
            FileTransferStatus.FAILED,
            FileTransferStatus.EXPIRED,
        ):
            _release_download_session(
                session,
                agent,
                error_message=session.error_message
                or (
                    "Session expired"
                    if session.status == FileTransferStatus.EXPIRED
                    else "Download released after failure"
                ),
                new_status=session.status,
            )
            return Response(
                {"session_id": str(session.session_id), "status": session.status}
            )

        reason, body_err = _body_str(request, "reason")
        if body_err:
            return body_err
        reason = (reason or "user").lower()
        if reason == "error":
            new_status = FileTransferStatus.FAILED
            error_message = "Download released after failure"
        else:
            new_status = FileTransferStatus.CANCELLED
            error_message = "Download cancelled by user"

        _release_download_session(
            session,
            agent,
            error_message=error_message,
            new_status=new_status,
        )
        return Response(
            {"session_id": str(session.session_id), "status": session.status}
        )


class CancelFileUpload(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id, session_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.UPLOAD,
        )

        if session.status in _FILE_TRANSFER_RELEASED_STATUSES:
            return Response(
                {"session_id": str(session.session_id), "status": session.status}
            )

        if session.status in (
            FileTransferStatus.FAILED,
            FileTransferStatus.EXPIRED,
        ):
            _release_upload_session(
                session,
                agent,
                error_message=session.error_message
                or (
                    "Session expired"
                    if session.status == FileTransferStatus.EXPIRED
                    else "Upload released after failure"
                ),
                new_status=session.status,
            )
            return Response(
                {"session_id": str(session.session_id), "status": session.status}
            )

        reason, body_err = _body_str(request, "reason")
        if body_err:
            return body_err
        reason = (reason or "user").lower()
        if reason == "error":
            new_status = FileTransferStatus.FAILED
            error_message = "Upload released after failure"
        else:
            new_status = FileTransferStatus.CANCELLED
            error_message = "Upload cancelled by user"

        _release_upload_session(
            session,
            agent,
            error_message=error_message,
            new_status=new_status,
        )
        return Response(
            {"session_id": str(session.session_id), "status": session.status}
        )


def _parse_file_transfer_warnings(raw) -> list:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except (ValueError, TypeError):
        pass
    return []


def _live_committed_offset(session: FileTransferSession) -> int:
    """DB committed_offset refined by the live Redis ACK when present."""
    if session.operation == FileTransferOperation.EXTRACT:
        return session.committed_offset
    if session.operation == FileTransferOperation.UPLOAD:
        redis_committed = get_upload_ack(session.session_id)
    else:
        redis_committed = get_download_ack(session.session_id)
    return max(session.committed_offset, redis_committed or 0)


class ListFileTransfers(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def get(self, request, agent_id):
        """List resumable file-transfer sessions for the current user on this agent."""
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        sessions = FileTransferSession.objects.filter(
            agent=agent,
            user=request.user,
            status__in=_FILE_TRANSFER_RESUMABLE_STATUSES,
            expires_at__gt=djangotime.now(),
        ).order_by("-updated_at")

        transfers = []
        for session in sessions:
            item = {
                "session_id": str(session.session_id),
                "operation": session.operation,
                "filename": session.filename,
                "destination_path": session.destination_path,
                "total_size": session.total_size,
                "chunk_size": session.chunk_size,
                "committed_offset": _live_committed_offset(session),
                "status": session.status,
                "expires_at": session.expires_at.isoformat(),
                "is_archive": bool(session.is_archive),
                "warnings": _parse_file_transfer_warnings(session.warnings),
            }
            if session.operation == FileTransferOperation.UPLOAD:
                item["conflict_policy"] = (
                    session.conflict_policy or FileTransferConflictPolicy.REPLACE
                )
            elif session.operation == FileTransferOperation.EXTRACT:
                item.update(_extract_progress_fields(session))
            transfers.append(item)

        return Response({"transfers": transfers})


class GetFileDownloadStatus(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def get(self, request, agent_id, session_id):
        """Lightweight status poll for a download session."""
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.DOWNLOAD,
        )

        if (
            session.status in _FILE_TRANSFER_ACTIVE_STATUSES
            and session.expires_at <= djangotime.now()
        ):
            _expire_transfer_session(session, agent)

        return Response(
            {
                "session_id": str(session.session_id),
                "status": session.status,
                "total_size": session.total_size,
                "chunk_size": session.chunk_size,
                "committed_offset": session.committed_offset,
                "filename": session.filename,
                "is_archive": session.is_archive,
                "warnings": _parse_file_transfer_warnings(session.warnings),
                "error": session.error_message,
            }
        )


def _extract_progress_fields(session: FileTransferSession) -> dict:
    return {
        "source_path": session.source_path,
        "conflict_policy": session.conflict_policy,
        "files_done": session.files_done,
        "files_total": session.files_total,
        "files_skipped": session.files_skipped,
    }


class InitFileExtract(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        paths = {}
        for key, field in (
            ("source_path", "The ZIP path"),
            ("destination_path", "The destination"),
        ):
            raw, body_err = _body_str(request, key)
            if body_err:
                return body_err
            if len(raw) > 4096:
                return notify_error(f"{field} is too long")
            value = normalize_file_browser_path(raw, agent.plat)
            path_err = validate_absolute_agent_path(value, agent.plat, field=field)
            if path_err:
                return notify_error(path_err)
            paths[key] = value
        source_path, destination_path = paths["source_path"], paths["destination_path"]

        filename = source_path.replace("\\", "/").split("/")[-1]
        if not filename.lower().endswith(".zip") or len(filename) > 255:
            return notify_error("Only .zip files can be extracted")

        policy, body_err = _body_str(request, "conflict_policy")
        if body_err:
            return body_err
        policy = (policy or FileTransferConflictPolicy.SKIP).lower()
        if policy not in FileTransferConflictPolicy.values:
            return notify_error("conflict_policy must be skip or replace")

        session = create_file_transfer_session_locked(
            agent,
            request.user,
            operation=FileTransferOperation.EXTRACT,
            status=FileTransferStatus.WAITING_FOR_AGENT,
            source_path=source_path,
            destination_path=destination_path,
            filename=filename,
            conflict_policy=policy,
            total_size=0,
            chunk_size=0,
            committed_offset=0,
            expires_at=djangotime.now()
            + dt.timedelta(minutes=FILE_TRANSFER_IDLE_EXPIRE_MINUTES),
        )
        if isinstance(session, Response):
            return session

        logger.info(
            "file_transfer extract init session=%s agent=%s user=%s source=%s destination=%s",
            session.session_id,
            agent.agent_id,
            request.user.pk,
            source_path,
            destination_path,
        )

        response = send_nats_command(
            agent,
            "files_extract_prepare",
            {
                "session_id": str(session.session_id),
                "source_path": source_path,
                "destination_path": destination_path,
                "conflict_policy": policy,
                "max_files": str(FILE_BROWSER_MAX_EXTRACT_FILES),
                "max_size_bytes": str(FILE_BROWSER_MAX_EXTRACT_SIZE_BYTES),
                "max_depth": str(FILE_BROWSER_MAX_EXTRACT_DEPTH),
            },
            timeout=30,
            prefix_error=False,
        )

        if isinstance(response, Response):
            _fail_transfer_session(session, agent, str(response.data))
            return response

        if not isinstance(response, dict) or response.get("status") != "extracting":
            error_message = (
                isinstance(response, dict) and response.get("error")
            ) or "Agent failed to start the extraction"
            _fail_transfer_session(session, agent, str(error_message))
            return notify_error(str(error_message))

        _audit_file_browser(
            request,
            agent,
            AuditActionType.MODIFY,
            "extract",
            [source_path],
            extra={
                "destination": destination_path,
                "conflict_policy": policy,
                "session_id": str(session.session_id),
            },
        )
        return Response(
            {"session_id": str(session.session_id), "status": session.status},
            status=status.HTTP_202_ACCEPTED,
        )


class GetFileExtractStatus(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def get(self, request, agent_id, session_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.EXTRACT,
        )

        if (
            session.status in _FILE_TRANSFER_ACTIVE_STATUSES
            and session.expires_at <= djangotime.now()
        ):
            _expire_transfer_session(session, agent)

        return Response(
            {
                "session_id": str(session.session_id),
                "status": session.status,
                "filename": session.filename,
                "destination_path": session.destination_path,
                "total_size": session.total_size,
                "committed_offset": session.committed_offset,
                "warnings": _parse_file_transfer_warnings(session.warnings),
                "error": session.error_message,
                **_extract_progress_fields(session),
            }
        )


class CancelFileExtract(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def post(self, request, agent_id, session_id):
        agent = get_validated_agent(
            agent_id, min_version=FILE_BROWSER_MIN_AGENT_VERSION
        )
        if isinstance(agent, Response):
            return agent

        session = get_object_or_404(
            FileTransferSession,
            session_id=session_id,
            agent=agent,
            user=request.user,
            operation=FileTransferOperation.EXTRACT,
        )

        if session.status in _FILE_TRANSFER_ACTIVE_STATUSES:
            _release_extract_session(
                session,
                agent,
                error_message="Extract cancelled by user",
                new_status=FileTransferStatus.CANCELLED,
            )
        return Response(
            {
                "session_id": str(session.session_id),
                "status": session.status,
                "files_done": session.files_done,
                "files_skipped": session.files_skipped,
            }
        )


class AgentTerminalDefaults(APIView):
    permission_classes = [IsAuthenticated, AgentTerminalPerms]

    def get(self, request, agent_id):
        agent = get_object_or_404(
            Agent.objects.filter_by_role(request.user).defer(*AGENT_DEFER),
            agent_id=agent_id,
        )

        supports_new_terminal = True
        if pyver.parse(agent.version) < pyver.parse("2.11.0"):
            supports_new_terminal = False

        core_settings = CoreSettings.objects.only("terminal_mode").first()
        return Response(
            AgentTerminalDefaultsSerializer(
                agent,
                context={
                    "core_settings": core_settings,
                    "supports_new_terminal": supports_new_terminal,
                },
            ).data
        )


class AgentFileBrowserDefaults(APIView):
    permission_classes = [IsAuthenticated, AgentFileBrowserPerms]

    def get(self, request, agent_id):
        agent = get_object_or_404(
            Agent.objects.filter_by_role(request.user).defer(*AGENT_DEFER),
            agent_id=agent_id,
        )

        supports_new_file_browser = True
        if pyver.parse(agent.version) < pyver.parse(FILE_BROWSER_MIN_AGENT_VERSION):
            supports_new_file_browser = False

        core_settings = CoreSettings.objects.only("file_browser_mode").first()
        return Response(
            AgentFileBrowserDefaultsSerializer(
                agent,
                context={
                    "core_settings": core_settings,
                    "supports_new_file_browser": supports_new_file_browser,
                },
            ).data
        )
