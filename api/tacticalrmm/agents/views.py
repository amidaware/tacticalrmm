import asyncio
from loguru import logger
import os
import subprocess
import pytz
import datetime as dt
from packaging import version as pyver

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics

from .models import Agent, AgentOutage, RecoveryAction, Note
from core.models import CoreSettings
from scripts.models import Script
from logs.models import AuditLog

from .serializers import (
    AgentSerializer,
    AgentHostnameSerializer,
    AgentTableSerializer,
    AgentEditSerializer,
    NoteSerializer,
    NotesSerializer,
)
from winupdate.serializers import WinUpdatePolicySerializer

from .tasks import uninstall_agent_task, send_agent_update_task
from winupdate.tasks import bulk_check_for_updates_task
from scripts.tasks import handle_bulk_command_task, handle_bulk_script_task

from tacticalrmm.utils import notify_error, reload_nats

logger.configure(**settings.LOG_CONFIG)


@api_view()
def get_agent_versions(request):
    agents = Agent.objects.only("pk")
    return Response(
        {
            "versions": [settings.LATEST_AGENT_VER],
            "agents": AgentHostnameSerializer(agents, many=True).data,
        }
    )


@api_view(["POST"])
def update_agents(request):
    pks = request.data["pks"]
    version = request.data["version"]
    send_agent_update_task.delay(pks=pks, version=version)
    return Response("ok")


@api_view()
def ping(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    status = "offline"
    if agent.has_nats:
        r = asyncio.run(agent.nats_cmd({"func": "ping"}, timeout=5))
        if r == "pong":
            status = "online"
    else:
        r = agent.salt_api_cmd(timeout=5, func="test.ping")
        if isinstance(r, bool) and r:
            status = "online"

    return Response({"name": agent.hostname, "status": status})


@api_view(["DELETE"])
def uninstall(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    if agent.has_nats:
        asyncio.run(agent.nats_cmd({"func": "uninstall"}, wait=False))

    salt_id = agent.salt_id
    name = agent.hostname
    has_nats = agent.has_nats
    agent.delete()
    reload_nats()

    uninstall_agent_task.delay(salt_id, has_nats)
    return Response(f"{name} will now be uninstalled.")


@api_view(["PATCH"])
def edit_agent(request):
    agent = get_object_or_404(Agent, pk=request.data["id"])

    old_site = agent.site.pk
    a_serializer = AgentSerializer(instance=agent, data=request.data, partial=True)
    a_serializer.is_valid(raise_exception=True)
    a_serializer.save()

    policy = agent.winupdatepolicy.get()
    p_serializer = WinUpdatePolicySerializer(
        instance=policy, data=request.data["winupdatepolicy"][0]
    )
    p_serializer.is_valid(raise_exception=True)
    p_serializer.save()

    # check if site changed and initiate generating correct policies
    if old_site != request.data["site"]:
        agent.generate_checks_from_policies(clear=True)
        agent.generate_tasks_from_policies(clear=True)

    return Response("ok")


@api_view()
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
    if not agent.has_nats:
        return notify_error("Requires agent version 1.1.0 or greater")
    r = asyncio.run(agent.nats_cmd(data={"func": "procs"}, timeout=5))
    if r == "timeout":
        return notify_error("Unable to contact the agent")

    return Response(r)


@api_view()
def kill_proc(request, pk, pid):
    agent = get_object_or_404(Agent, pk=pk)
    if not agent.has_nats:
        return notify_error("Requires agent version 1.1.0 or greater")

    r = asyncio.run(
        agent.nats_cmd({"func": "killproc", "procpid": int(pid)}, timeout=15)
    )

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r != "ok":
        return notify_error(r)

    return Response("ok")


@api_view()
def get_event_log(request, pk, logtype, days):
    agent = get_object_or_404(Agent, pk=pk)
    if not agent.has_nats:
        return notify_error("Requires agent version 1.1.0 or greater")
    data = {
        "func": "eventlog",
        "timeout": 30,
        "payload": {
            "logname": logtype,
            "days": str(days),
        },
    }
    r = asyncio.run(agent.nats_cmd(data, timeout=32))
    if r == "timeout":
        return notify_error("Unable to contact the agent")

    return Response(r)


@api_view(["POST"])
def power_action(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    if not agent.has_nats:
        return notify_error("Requires agent version 1.1.0 or greater")
    if request.data["action"] == "rebootnow":
        r = asyncio.run(agent.nats_cmd({"func": "rebootnow"}, timeout=10))
        if r != "ok":
            return notify_error("Unable to contact the agent")

    return Response("ok")


@api_view(["POST"])
def send_raw_cmd(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    if not agent.has_nats:
        return notify_error("Requires agent version 1.1.0 or greater")
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


class AgentsTableList(generics.ListAPIView):
    queryset = (
        Agent.objects.select_related("site")
        .prefetch_related("agentchecks")
        .only(
            "pk",
            "hostname",
            "agent_id",
            "site",
            "monitoring_type",
            "description",
            "needs_reboot",
            "overdue_text_alert",
            "overdue_email_alert",
            "overdue_time",
            "last_seen",
            "boot_time",
            "logged_in_username",
            "last_logged_in_user",
            "time_zone",
            "maintenance_mode",
        )
    )
    serializer_class = AgentTableSerializer

    def list(self, request):
        queryset = self.get_queryset()
        ctx = {
            "default_tz": pytz.timezone(CoreSettings.objects.first().default_time_zone)
        }
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


@api_view()
def by_client(request, clientpk):
    agents = (
        Agent.objects.select_related("site")
        .filter(site__client_id=clientpk)
        .prefetch_related("agentchecks")
        .only(
            "pk",
            "hostname",
            "agent_id",
            "site",
            "monitoring_type",
            "description",
            "needs_reboot",
            "overdue_text_alert",
            "overdue_email_alert",
            "overdue_time",
            "last_seen",
            "boot_time",
            "logged_in_username",
            "last_logged_in_user",
            "time_zone",
            "maintenance_mode",
        )
    )
    ctx = {"default_tz": pytz.timezone(CoreSettings.objects.first().default_time_zone)}
    return Response(AgentTableSerializer(agents, many=True, context=ctx).data)


@api_view()
def by_site(request, sitepk):
    agents = (
        Agent.objects.filter(site_id=sitepk)
        .select_related("site")
        .prefetch_related("agentchecks")
        .only(
            "pk",
            "hostname",
            "agent_id",
            "site",
            "monitoring_type",
            "description",
            "needs_reboot",
            "overdue_text_alert",
            "overdue_email_alert",
            "overdue_time",
            "last_seen",
            "boot_time",
            "logged_in_username",
            "last_logged_in_user",
            "time_zone",
            "maintenance_mode",
        )
    )
    ctx = {"default_tz": pytz.timezone(CoreSettings.objects.first().default_time_zone)}
    return Response(AgentTableSerializer(agents, many=True, context=ctx).data)


@api_view(["POST"])
def overdue_action(request):
    pk = request.data["pk"]
    alert_type = request.data["alertType"]
    action = request.data["action"]
    agent = get_object_or_404(Agent, pk=pk)
    if alert_type == "email" and action == "enabled":
        agent.overdue_email_alert = True
        agent.save(update_fields=["overdue_email_alert"])
    elif alert_type == "email" and action == "disabled":
        agent.overdue_email_alert = False
        agent.save(update_fields=["overdue_email_alert"])
    elif alert_type == "text" and action == "enabled":
        agent.overdue_text_alert = True
        agent.save(update_fields=["overdue_text_alert"])
    elif alert_type == "text" and action == "disabled":
        agent.overdue_text_alert = False
        agent.save(update_fields=["overdue_text_alert"])
    else:
        return Response(
            {"error": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST
        )
    return Response(agent.hostname)


@api_view(["POST"])
def reboot_later(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    date_time = request.data["datetime"]

    try:
        obj = dt.datetime.strptime(date_time, "%Y-%m-%d %H:%M")
    except Exception:
        return notify_error("Invalid date")

    r = agent.schedule_reboot(obj)

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "failed":
        return notify_error("Something went wrong")

    return Response(r["msg"])


@api_view(["POST"])
def install_agent(request):
    from knox.models import AuthToken

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
    download_url = settings.DL_64 if arch == "64" else settings.DL_32

    _, token = AuthToken.objects.create(
        user=request.user, expiry=dt.timedelta(hours=request.data["expires"])
    )

    if request.data["installMethod"] == "exe":
        go_bin = "/usr/local/rmmgo/go/bin/go"

        if not os.path.exists(go_bin):
            return Response("nogolang", status=status.HTTP_409_CONFLICT)

        api = request.data["api"]
        atype = request.data["agenttype"]
        rdp = request.data["rdp"]
        ping = request.data["ping"]
        power = request.data["power"]

        file_name = "rmm-installer.exe"
        exe = os.path.join(settings.EXE_DIR, file_name)

        if os.path.exists(exe):
            try:
                os.remove(exe)
            except Exception as e:
                logger.error(str(e))

        goarch = "amd64" if arch == "64" else "386"
        cmd = [
            "env",
            "GOOS=windows",
            f"GOARCH={goarch}",
            go_bin,
            "build",
            f"-ldflags=\"-X 'main.Inno={inno}'",
            f"-X 'main.Api={api}'",
            f"-X 'main.Client={client_id}'",
            f"-X 'main.Site={site_id}'",
            f"-X 'main.Atype={atype}'",
            f"-X 'main.Rdp={rdp}'",
            f"-X 'main.Ping={ping}'",
            f"-X 'main.Power={power}'",
            f"-X 'main.DownloadUrl={download_url}'",
            f"-X 'main.Token={token}'\"",
            "-o",
            exe,
        ]

        build_error = False
        gen_error = False

        gen = [
            "env",
            "GOOS=windows",
            f"GOARCH={goarch}",
            go_bin,
            "generate",
        ]
        try:
            r1 = subprocess.run(
                " ".join(gen),
                capture_output=True,
                shell=True,
                cwd=os.path.join(settings.BASE_DIR, "core/goinstaller"),
            )
        except Exception as e:
            gen_error = True
            logger.error(str(e))
            return Response(
                "genfailed", status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        if r1.returncode != 0:
            gen_error = True
            if r1.stdout:
                logger.error(r1.stdout.decode("utf-8", errors="ignore"))

            if r1.stderr:
                logger.error(r1.stderr.decode("utf-8", errors="ignore"))

            logger.error(f"Go build failed with return code {r1.returncode}")

        if gen_error:
            return Response(
                "genfailed", status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        try:
            r = subprocess.run(
                " ".join(cmd),
                capture_output=True,
                shell=True,
                cwd=os.path.join(settings.BASE_DIR, "core/goinstaller"),
            )
        except Exception as e:
            build_error = True
            logger.error(str(e))
            return Response("buildfailed", status=status.HTTP_412_PRECONDITION_FAILED)

        if r.returncode != 0:
            build_error = True
            if r.stdout:
                logger.error(r.stdout.decode("utf-8", errors="ignore"))

            if r.stderr:
                logger.error(r.stderr.decode("utf-8", errors="ignore"))

            logger.error(f"Go build failed with return code {r.returncode}")

        if build_error:
            return Response("buildfailed", status=status.HTTP_412_PRECONDITION_FAILED)

        if settings.DEBUG:
            with open(exe, "rb") as f:
                response = HttpResponse(
                    f.read(),
                    content_type="application/vnd.microsoft.portable-executable",
                )
                response["Content-Disposition"] = f"inline; filename={file_name}"
                return response
        else:
            response = HttpResponse()
            response["Content-Disposition"] = f"attachment; filename={file_name}"
            response["X-Accel-Redirect"] = f"/private/exe/{file_name}"
            return response

    elif request.data["installMethod"] == "manual":
        cmd = [
            inno,
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "&&",
            "timeout",
            "/t",
            "10",
            "/nobreak",
            ">",
            "NUL",
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
            "salt64": settings.SALT_64,
            "salt32": settings.SALT_32,
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

    if pyver.parse(agent.version) <= pyver.parse("0.9.5"):
        return notify_error("Only available in agent version greater than 0.9.5")

    if not agent.has_nats:
        if mode == "tacagent" or mode == "checkrunner" or mode == "rpc":
            return notify_error("Requires agent version 1.1.0 or greater")

    # attempt a realtime recovery if supported, otherwise fall back to old recovery method
    if agent.has_nats:
        if (
            mode == "tacagent"
            or mode == "checkrunner"
            or mode == "salt"
            or mode == "mesh"
        ):
            data = {"func": "recover", "payload": {"mode": mode}}
            r = asyncio.run(agent.nats_cmd(data, timeout=10))
            if r == "ok":
                return Response("Successfully completed recovery")

    if agent.recoveryactions.filter(last_run=None).exists():
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
def run_script(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    if not agent.has_nats:
        return notify_error("Requires agent version 1.1.0 or greater")
    script = get_object_or_404(Script, pk=request.data["scriptPK"])
    output = request.data["output"]
    req_timeout = int(request.data["timeout"]) + 3

    AuditLog.audit_script_run(
        username=request.user.username,
        hostname=agent.hostname,
        script=script.name,
    )

    data = {
        "func": "runscript",
        "timeout": request.data["timeout"],
        "script_args": request.data["args"],
        "payload": {
            "code": script.code,
            "shell": script.shell,
        },
    }

    if output == "wait":
        r = asyncio.run(agent.nats_cmd(data, timeout=req_timeout))
        return Response(r)
    else:
        asyncio.run(agent.nats_cmd(data, wait=False))
        return Response(f"{script.name} will now be run on {agent.hostname}")


@api_view()
def recover_mesh(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    if not agent.has_nats:
        return notify_error("Requires agent version 1.1.0 or greater")

    data = {"func": "recover", "payload": {"mode": "mesh"}}
    r = asyncio.run(agent.nats_cmd(data, timeout=45))
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
        q = Agent.objects.all()
    else:
        return notify_error("Something went wrong")

    minions = [agent.salt_id for agent in q]
    agents = [agent.pk for agent in q]

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
        r = Agent.salt_batch_async(minions=minions, func="win_agent.install_updates")
        if r == "timeout":
            return notify_error("Salt API not running")
        return Response(
            f"Pending updates will now be installed on {len(agents)} agents"
        )
    elif request.data["mode"] == "scan":
        bulk_check_for_updates_task.delay(minions=minions)
        return Response(f"Patch status scan will now run on {len(agents)} agents")

    return notify_error("Something went wrong")


@api_view(["POST"])
def agent_counts(request):
    return Response(
        {
            "total_server_count": Agent.objects.filter(
                monitoring_type="server"
            ).count(),
            "total_server_offline_count": AgentOutage.objects.filter(
                recovery_time=None, agent__monitoring_type="server"
            ).count(),
            "total_workstation_count": Agent.objects.filter(
                monitoring_type="workstation"
            ).count(),
            "total_workstation_offline_count": AgentOutage.objects.filter(
                recovery_time=None, agent__monitoring_type="workstation"
            ).count(),
        }
    )


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
