import asyncio
import datetime as dt
import os
import random
import string
import time

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from loguru import logger
from packaging import version as pyver
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import CoreSettings
from logs.models import AuditLog, PendingAction
from scripts.models import Script
from scripts.tasks import handle_bulk_command_task, handle_bulk_script_task
from tacticalrmm.utils import get_default_timezone, notify_error, reload_nats
from winupdate.serializers import WinUpdatePolicySerializer
from winupdate.tasks import bulk_check_for_updates_task, bulk_install_updates_task

from .models import Agent, AgentCustomField, Note, RecoveryAction
from .permissions import (
    EditAgentPerms,
    EvtLogPerms,
    InstallAgentPerms,
    ManageNotesPerms,
    ManageProcPerms,
    MeshPerms,
    RebootAgentPerms,
    RunBulkPerms,
    RunScriptPerms,
    SendCMDPerms,
    UninstallPerms,
    UpdateAgentPerms,
)
from .serializers import (
    AgentCustomFieldSerializer,
    AgentEditSerializer,
    AgentHostnameSerializer,
    AgentOverdueActionSerializer,
    AgentSerializer,
    AgentTableSerializer,
    NoteSerializer,
    NotesSerializer,
)
from .tasks import run_script_email_results_task, send_agent_update_task

logger.configure(**settings.LOG_CONFIG)


@api_view()
def get_agent_versions(request):
    agents = Agent.objects.prefetch_related("site").only("pk", "hostname")
    return Response(
        {
            "versions": [settings.LATEST_AGENT_VER],
            "agents": AgentHostnameSerializer(agents, many=True).data,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, UpdateAgentPerms])
def update_agents(request):
    q = Agent.objects.filter(pk__in=request.data["pks"]).only("pk", "version")
    pks: list[int] = [
        i.pk
        for i in q
        if pyver.parse(i.version) < pyver.parse(settings.LATEST_AGENT_VER)
    ]
    send_agent_update_task.delay(pks=pks)
    return Response("ok")


@api_view()
@permission_classes([IsAuthenticated, UninstallPerms])
def ping(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    status = "offline"
    attempts = 0
    while 1:
        r = asyncio.run(agent.nats_cmd({"func": "ping"}, timeout=2))
        if r == "pong":
            status = "online"
            break
        else:
            attempts += 1
            time.sleep(1)

        if attempts >= 5:
            break

    return Response({"name": agent.hostname, "status": status})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, UninstallPerms])
def uninstall(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    asyncio.run(agent.nats_cmd({"func": "uninstall"}, wait=False))
    name = agent.hostname
    agent.delete()
    reload_nats()
    return Response(f"{name} will now be uninstalled.")


@api_view(["PATCH", "PUT"])
@permission_classes([IsAuthenticated, EditAgentPerms])
def edit_agent(request):
    agent = get_object_or_404(Agent, pk=request.data["id"])

    a_serializer = AgentSerializer(instance=agent, data=request.data, partial=True)
    a_serializer.is_valid(raise_exception=True)
    a_serializer.save()

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
            custom_field["agent"] = agent.id  # type: ignore

            if AgentCustomField.objects.filter(
                field=field["field"], agent=agent.id  # type: ignore
            ):
                value = AgentCustomField.objects.get(
                    field=field["field"], agent=agent.id  # type: ignore
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

    return Response("ok")


@api_view()
@permission_classes([IsAuthenticated, MeshPerms])
def meshcentral(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    core = CoreSettings.objects.first()

    token = agent.get_login_token(
        key=core.mesh_token, user=f"user//{core.mesh_username}"
    )

    if token == "err":
        return notify_error("Invalid mesh token")

    control = f"{core.mesh_site}/?login={token}&gotonode={agent.mesh_node_id}&viewmode=11&hide=31"
    terminal = f"{core.mesh_site}/?login={token}&gotonode={agent.mesh_node_id}&viewmode=12&hide=31"
    file = f"{core.mesh_site}/?login={token}&gotonode={agent.mesh_node_id}&viewmode=13&hide=31"

    AuditLog.audit_mesh_session(username=request.user.username, hostname=agent.hostname)

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


@api_view()
def agent_detail(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(AgentSerializer(agent).data)


@api_view()
def get_processes(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    r = asyncio.run(agent.nats_cmd(data={"func": "procs"}, timeout=5))
    if r == "timeout":
        return notify_error("Unable to contact the agent")
    return Response(r)


@api_view()
@permission_classes([IsAuthenticated, ManageProcPerms])
def kill_proc(request, pk, pid):
    agent = get_object_or_404(Agent, pk=pk)
    r = asyncio.run(
        agent.nats_cmd({"func": "killproc", "procpid": int(pid)}, timeout=15)
    )

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r != "ok":
        return notify_error(r)

    return Response("ok")


@api_view()
@permission_classes([IsAuthenticated, EvtLogPerms])
def get_event_log(request, pk, logtype, days):
    agent = get_object_or_404(Agent, pk=pk)
    timeout = 180 if logtype == "Security" else 30
    data = {
        "func": "eventlog",
        "timeout": timeout,
        "payload": {
            "logname": logtype,
            "days": str(days),
        },
    }
    r = asyncio.run(agent.nats_cmd(data, timeout=timeout + 2))
    if r == "timeout":
        return notify_error("Unable to contact the agent")

    return Response(r)


@api_view(["POST"])
@permission_classes([IsAuthenticated, SendCMDPerms])
def send_raw_cmd(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    timeout = int(request.data["timeout"])
    data = {
        "func": "rawcmd",
        "timeout": timeout,
        "payload": {
            "command": request.data["cmd"],
            "shell": request.data["shell"],
        },
    }
    r = asyncio.run(agent.nats_cmd(data, timeout=timeout + 2))

    if r == "timeout":
        return notify_error("Unable to contact the agent")

    AuditLog.audit_raw_command(
        username=request.user.username,
        hostname=agent.hostname,
        cmd=request.data["cmd"],
        shell=request.data["shell"],
    )

    return Response(r)


class AgentsTableList(APIView):
    def patch(self, request):
        if "sitePK" in request.data.keys():
            queryset = (
                Agent.objects.select_related("site", "policy", "alert_template")
                .prefetch_related("agentchecks")
                .filter(site_id=request.data["sitePK"])
            )
        elif "clientPK" in request.data.keys():
            queryset = (
                Agent.objects.select_related("site", "policy", "alert_template")
                .prefetch_related("agentchecks")
                .filter(site__client_id=request.data["clientPK"])
            )
        else:
            queryset = Agent.objects.select_related(
                "site", "policy", "alert_template"
            ).prefetch_related("agentchecks")

        queryset = queryset.only(
            "pk",
            "hostname",
            "agent_id",
            "site",
            "policy",
            "alert_template",
            "monitoring_type",
            "description",
            "needs_reboot",
            "overdue_text_alert",
            "overdue_email_alert",
            "overdue_time",
            "offline_time",
            "last_seen",
            "boot_time",
            "logged_in_username",
            "last_logged_in_user",
            "time_zone",
            "maintenance_mode",
            "pending_actions_count",
            "has_patches_pending",
        )
        ctx = {"default_tz": get_default_timezone()}
        serializer = AgentTableSerializer(queryset, many=True, context=ctx)
        return Response(serializer.data)


@api_view()
def list_agents_no_detail(request):
    agents = Agent.objects.select_related("site").only("pk", "hostname", "site")
    return Response(AgentHostnameSerializer(agents, many=True).data)


@api_view()
def agent_edit_details(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(AgentEditSerializer(agent).data)


@api_view(["POST"])
def overdue_action(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    serializer = AgentOverdueActionSerializer(
        instance=agent, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(agent.hostname)


class Reboot(APIView):
    permission_classes = [IsAuthenticated, RebootAgentPerms]
    # reboot now
    def post(self, request):
        agent = get_object_or_404(Agent, pk=request.data["pk"])
        r = asyncio.run(agent.nats_cmd({"func": "rebootnow"}, timeout=10))
        if r != "ok":
            return notify_error("Unable to contact the agent")

        return Response("ok")

    # reboot later
    def patch(self, request):
        agent = get_object_or_404(Agent, pk=request.data["pk"])

        try:
            obj = dt.datetime.strptime(request.data["datetime"], "%Y-%m-%d %H:%M")
        except Exception:
            return notify_error("Invalid date")

        task_name = "TacticalRMM_SchedReboot_" + "".join(
            random.choice(string.ascii_letters) for _ in range(10)
        )

        nats_data = {
            "func": "schedtask",
            "schedtaskpayload": {
                "type": "schedreboot",
                "deleteafter": True,
                "trigger": "once",
                "name": task_name,
                "year": int(dt.datetime.strftime(obj, "%Y")),
                "month": dt.datetime.strftime(obj, "%B"),
                "day": int(dt.datetime.strftime(obj, "%d")),
                "hour": int(dt.datetime.strftime(obj, "%H")),
                "min": int(dt.datetime.strftime(obj, "%M")),
            },
        }

        r = asyncio.run(agent.nats_cmd(nats_data, timeout=10))
        if r != "ok":
            return notify_error(r)

        details = {"taskname": task_name, "time": str(obj)}
        PendingAction.objects.create(
            agent=agent, action_type="schedreboot", details=details
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

    from agents.utils import get_winagent_url

    client_id = request.data["client"]
    site_id = request.data["site"]
    version = settings.LATEST_AGENT_VER
    arch = request.data["arch"]

    # response type is blob so we have to use
    # status codes and render error message on the frontend
    if arch == "64" and not os.path.exists(
        os.path.join(settings.EXE_DIR, "meshagent.exe")
    ):
        return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

    if arch == "32" and not os.path.exists(
        os.path.join(settings.EXE_DIR, "meshagent-x86.exe")
    ):
        return Response(status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    inno = (
        f"winagent-v{version}.exe" if arch == "64" else f"winagent-v{version}-x86.exe"
    )
    download_url = get_winagent_url(arch)

    installer_user = User.objects.filter(is_installer_user=True).first()

    _, token = AuthToken.objects.create(
        user=installer_user, expiry=dt.timedelta(hours=request.data["expires"])
    )

    if request.data["installMethod"] == "exe":
        from tacticalrmm.utils import generate_winagent_exe

        return generate_winagent_exe(
            client=client_id,
            site=site_id,
            agent_type=request.data["agenttype"],
            rdp=request.data["rdp"],
            ping=request.data["ping"],
            power=request.data["power"],
            arch=arch,
            token=token,
            api=request.data["api"],
            file_name=request.data["fileName"],
        )

    elif request.data["installMethod"] == "manual":
        cmd = [
            inno,
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "&&",
            "ping",
            "127.0.0.1",
            "-n",
            "5",
            "&&",
            r'"C:\Program Files\TacticalAgent\tacticalrmm.exe"',
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

        if int(request.data["rdp"]):
            cmd.append("--rdp")
        if int(request.data["ping"]):
            cmd.append("--ping")
        if int(request.data["power"]):
            cmd.append("--power")

        resp = {
            "cmd": " ".join(str(i) for i in cmd),
            "url": download_url,
        }

        return Response(resp)

    elif request.data["installMethod"] == "powershell":

        ps = os.path.join(settings.BASE_DIR, "core/installer.ps1")

        with open(ps, "r") as f:
            text = f.read()

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

        file_name = "rmm-installer.ps1"
        ps1 = os.path.join(settings.EXE_DIR, file_name)

        if os.path.exists(ps1):
            try:
                os.remove(ps1)
            except Exception as e:
                logger.error(str(e))

        with open(ps1, "w") as f:
            f.write(text)

        if settings.DEBUG:
            with open(ps1, "r") as f:
                response = HttpResponse(f.read(), content_type="text/plain")
                response["Content-Disposition"] = f"inline; filename={file_name}"
                return response
        else:
            response = HttpResponse()
            response["Content-Disposition"] = f"attachment; filename={file_name}"
            response["X-Accel-Redirect"] = f"/private/exe/{file_name}"
            return response


@api_view(["POST"])
def recover(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    mode = request.data["mode"]

    # attempt a realtime recovery, otherwise fall back to old recovery method
    if mode == "tacagent" or mode == "mesh":
        data = {"func": "recover", "payload": {"mode": mode}}
        r = asyncio.run(agent.nats_cmd(data, timeout=10))
        if r == "ok":
            return Response("Successfully completed recovery")

    if agent.recoveryactions.filter(last_run=None).exists():  # type: ignore
        return notify_error(
            "A recovery action is currently pending. Please wait for the next agent check-in."
        )

    if mode == "command" and not request.data["cmd"]:
        return notify_error("Command is required")

    # if we've made it this far and realtime recovery didn't work,
    # tacagent service is the fallback recovery so we obv can't use that to recover itself if it's down
    if mode == "tacagent":
        return notify_error(
            "Requires RPC service to be functional. Please recover that first"
        )

    # we should only get here if all other methods fail
    RecoveryAction(
        agent=agent,
        mode=mode,
        command=request.data["cmd"] if mode == "command" else None,
    ).save()

    return Response("Recovery will be attempted on the agent's next check-in")


@api_view(["POST"])
@permission_classes([IsAuthenticated, RunScriptPerms])
def run_script(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    script = get_object_or_404(Script, pk=request.data["scriptPK"])
    output = request.data["output"]
    args = request.data["args"]
    req_timeout = int(request.data["timeout"]) + 3

    AuditLog.audit_script_run(
        username=request.user.username,
        hostname=agent.hostname,
        script=script.name,
    )

    if output == "wait":
        r = agent.run_script(
            scriptpk=script.pk, args=args, timeout=req_timeout, wait=True
        )
        return Response(r)

    elif output == "email":
        emails = (
            [] if request.data["emailmode"] == "default" else request.data["emails"]
        )
        run_script_email_results_task.delay(
            agentpk=agent.pk,
            scriptpk=script.pk,
            nats_timeout=req_timeout,
            emails=emails,
            args=args,
        )
    else:
        agent.run_script(scriptpk=script.pk, args=args, timeout=req_timeout)

    return Response(f"{script.name} will now be run on {agent.hostname}")


@api_view()
def recover_mesh(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    data = {"func": "recover", "payload": {"mode": "mesh"}}
    r = asyncio.run(agent.nats_cmd(data, timeout=90))
    if r != "ok":
        return notify_error("Unable to contact the agent")

    return Response(f"Repaired mesh agent on {agent.hostname}")


@api_view(["POST"])
def get_mesh_exe(request, arch):
    filename = "meshagent.exe" if arch == "64" else "meshagent-x86.exe"
    mesh_exe = os.path.join(settings.EXE_DIR, filename)
    if not os.path.exists(mesh_exe):
        return notify_error(f"File {filename} has not been uploaded.")

    if settings.DEBUG:
        with open(mesh_exe, "rb") as f:
            response = HttpResponse(
                f.read(), content_type="application/vnd.microsoft.portable-executable"
            )
            response["Content-Disposition"] = f"inline; filename={filename}"
            return response
    else:
        response = HttpResponse()
        response["Content-Disposition"] = f"attachment; filename={filename}"
        response["X-Accel-Redirect"] = f"/private/exe/{filename}"
        return response


class GetAddNotes(APIView):
    def get(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)
        return Response(NotesSerializer(agent).data)

    def post(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)
        serializer = NoteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(agent=agent, user=request.user)
        return Response("Note added!")


class GetEditDeleteNote(APIView):
    permission_classes = [IsAuthenticated, ManageNotesPerms]

    def get(self, request, pk):
        note = get_object_or_404(Note, pk=pk)
        return Response(NoteSerializer(note).data)

    def patch(self, request, pk):
        note = get_object_or_404(Note, pk=pk)
        serializer = NoteSerializer(instance=note, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("Note edited!")

    def delete(self, request, pk):
        note = get_object_or_404(Note, pk=pk)
        note.delete()
        return Response("Note was deleted!")


@api_view(["POST"])
@permission_classes([IsAuthenticated, RunBulkPerms])
def bulk(request):
    if request.data["target"] == "agents" and not request.data["agentPKs"]:
        return notify_error("Must select at least 1 agent")

    if request.data["target"] == "client":
        q = Agent.objects.filter(site__client_id=request.data["client"])
    elif request.data["target"] == "site":
        q = Agent.objects.filter(site_id=request.data["site"])
    elif request.data["target"] == "agents":
        q = Agent.objects.filter(pk__in=request.data["agentPKs"])
    elif request.data["target"] == "all":
        q = Agent.objects.only("pk", "monitoring_type")
    else:
        return notify_error("Something went wrong")

    if request.data["monType"] == "servers":
        q = q.filter(monitoring_type="server")
    elif request.data["monType"] == "workstations":
        q = q.filter(monitoring_type="workstation")

    agents: list[int] = [agent.pk for agent in q]

    AuditLog.audit_bulk_action(request.user, request.data["mode"], request.data)

    if request.data["mode"] == "command":
        handle_bulk_command_task.delay(
            agents, request.data["cmd"], request.data["shell"], request.data["timeout"]
        )
        return Response(f"Command will now be run on {len(agents)} agents")

    elif request.data["mode"] == "script":
        script = get_object_or_404(Script, pk=request.data["scriptPK"])
        handle_bulk_script_task.delay(
            script.pk, agents, request.data["args"], request.data["timeout"]
        )
        return Response(f"{script.name} will now be run on {len(agents)} agents")

    elif request.data["mode"] == "install":
        bulk_install_updates_task.delay(agents)
        return Response(
            f"Pending updates will now be installed on {len(agents)} agents"
        )
    elif request.data["mode"] == "scan":
        bulk_check_for_updates_task.delay(agents)
        return Response(f"Patch status scan will now run on {len(agents)} agents")

    return notify_error("Something went wrong")


@api_view(["POST"])
def agent_maintenance(request):
    if request.data["type"] == "Client":
        Agent.objects.filter(site__client_id=request.data["id"]).update(
            maintenance_mode=request.data["action"]
        )

    elif request.data["type"] == "Site":
        Agent.objects.filter(site_id=request.data["id"]).update(
            maintenance_mode=request.data["action"]
        )

    elif request.data["type"] == "Agent":
        agent = Agent.objects.get(pk=request.data["id"])
        agent.maintenance_mode = request.data["action"]
        agent.save(update_fields=["maintenance_mode"])

    else:
        return notify_error("Invalid data")

    return Response("ok")


class WMI(APIView):
    def get(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk)
        r = asyncio.run(agent.nats_cmd({"func": "sysinfo"}, timeout=20))
        if r != "ok":
            return notify_error("Unable to contact the agent")
        return Response("ok")
