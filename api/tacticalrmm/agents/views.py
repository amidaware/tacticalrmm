from loguru import logger
import os
import subprocess
import tempfile
import zlib
import json
import base64
import datetime as dt
from packaging import version as pyver

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.authentication import BasicAuthentication, TokenAuthentication

from .models import Agent, RecoveryAction, Note
from winupdate.models import WinUpdatePolicy
from clients.models import Client, Site
from accounts.models import User
from core.models import CoreSettings
from scripts.models import Script

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

from tacticalrmm.utils import notify_error

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
    r = agent.salt_api_cmd(timeout=5, func="test.ping")

    if r == "timeout" or r == "error":
        return Response({"name": agent.hostname, "status": "offline"})

    if isinstance(r, bool) and r:
        return Response({"name": agent.hostname, "status": "online"})
    else:
        return Response({"name": agent.hostname, "status": "offline"})


@api_view(["DELETE"])
def uninstall(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    salt_id = agent.salt_id
    name = agent.hostname
    agent.delete()

    # just in case agent-user gets deleted accidentaly from django-admin
    # we can still remove the agent
    try:
        user = User.objects.get(username=agent.agent_id)
        user.delete()
    except:
        pass

    uninstall_agent_task.delay(salt_id)
    return Response(f"{name} will now be uninstalled.")


@api_view(["PATCH"])
def edit_agent(request):
    agent = get_object_or_404(Agent, pk=request.data["id"])
    a_serializer = AgentSerializer(instance=agent, data=request.data, partial=True)
    a_serializer.is_valid(raise_exception=True)
    a_serializer.save()

    policy = WinUpdatePolicy.objects.get(agent=agent)
    p_serializer = WinUpdatePolicySerializer(
        instance=policy, data=request.data["winupdatepolicy"][0]
    )
    p_serializer.is_valid(raise_exception=True)
    p_serializer.save()

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

    control = (
        f"{core.mesh_site}/?login={token}&node={agent.mesh_node_id}&viewmode=11&hide=31"
    )
    terminal = (
        f"{core.mesh_site}/?login={token}&node={agent.mesh_node_id}&viewmode=12&hide=31"
    )
    file = (
        f"{core.mesh_site}/?login={token}&node={agent.mesh_node_id}&viewmode=13&hide=31"
    )
    webrdp = f"{core.mesh_site}/mstsc.html?login={token}&node={agent.mesh_node_id}"

    ret = {
        "hostname": agent.hostname,
        "control": control,
        "terminal": terminal,
        "file": file,
        "webrdp": webrdp,
        "status": agent.status,
    }
    return Response(ret)


@api_view()
def agent_detail(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(AgentSerializer(agent).data)


@api_view()
def get_processes(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(timeout=20, func="win_agent.get_procs")

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error":
        return notify_error("Something went wrong")

    return Response(r)


@api_view()
def kill_proc(request, pk, pid):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(timeout=25, func="ps.kill_pid", arg=int(pid))

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error":
        return notify_error("Something went wrong")

    if isinstance(r, bool) and not r:
        return notify_error("Unable to kill the process")

    return Response("ok")


@api_view()
def get_event_log(request, pk, logtype, days):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(
        timeout=30,
        func="win_agent.get_eventlog",
        arg=[logtype, int(days)],
    )

    if r == "timeout" or r == "error":
        return notify_error("Unable to contact the agent")

    return Response(json.loads(zlib.decompress(base64.b64decode(r["wineventlog"]))))


@api_view(["POST"])
def power_action(request):
    pk = request.data["pk"]
    action = request.data["action"]
    agent = get_object_or_404(Agent, pk=pk)
    if action == "rebootnow":
        logger.info(f"{agent.hostname} was scheduled for immediate reboot")
        r = agent.salt_api_cmd(
            timeout=30,
            func="system.reboot",
            arg=3,
            kwargs={"in_seconds": True},
        )
    if r == "timeout" or r == "error" or (isinstance(r, bool) and not r):
        return notify_error("Unable to contact the agent")

    return Response("ok")


@api_view(["POST"])
def send_raw_cmd(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])

    r = agent.salt_api_cmd(
        timeout=request.data["timeout"],
        func="cmd.run",
        kwargs={
            "cmd": request.data["cmd"],
            "shell": request.data["shell"],
            "timeout": request.data["timeout"],
        },
    )

    if r == "timeout":
        return notify_error("Unable to contact the agent")
    elif r == "error" or not r:
        return notify_error("Something went wrong")

    logger.info(f"The command {request.data['cmd']} was sent on agent {agent.hostname}")
    return Response(r)


@api_view()
def list_agents(request):
    agents = Agent.objects.all()
    return Response(AgentTableSerializer(agents, many=True).data)


@api_view()
def list_agents_no_detail(request):
    agents = Agent.objects.all()
    return Response(AgentHostnameSerializer(agents, many=True).data)


@api_view()
def agent_edit_details(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(AgentEditSerializer(agent).data)


@api_view()
def by_client(request, client):
    agents = Agent.objects.filter(client=client)
    return Response(AgentTableSerializer(agents, many=True).data)


@api_view()
def by_site(request, client, site):
    agents = Agent.objects.filter(client=client).filter(site=site)
    return Response(AgentTableSerializer(agents, many=True).data)


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

    client = get_object_or_404(Client, client=request.data["client"])
    site = get_object_or_404(Site, client=client, site=request.data["site"])
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
            f"-X 'main.Client={client.pk}'",
            f"-X 'main.Site={site.pk}'",
            f"-X 'main.Atype={atype}'",
            f"-X 'main.Rdp={rdp}'",
            f"-X 'main.Ping={ping}'",
            f"-X 'main.Power={power}'",
            f"-X 'main.DownloadUrl={download_url}'",
            f"-X 'main.Token={token}'\"",
            "-o",
            exe,
            os.path.join(settings.BASE_DIR, "core/installer.go"),
        ]

        build_error = False

        try:
            r = subprocess.run(" ".join(cmd), capture_output=True, shell=True)
        except Exception as e:
            build_error = True
            logger.error(str(e))

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
            "20",
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
            client.pk,
            "--site-id",
            site.pk,
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

        resp = {"cmd": " ".join(str(i) for i in cmd), "url": download_url}

        return Response(resp)

    elif request.data["installMethod"] == "powershell":

        ps = os.path.join(settings.BASE_DIR, "core/installer.ps1")

        with open(ps, "r") as f:
            text = f.read()

        replace_dict = {
            "innosetupchange": inno,
            "clientchange": str(client.pk),
            "sitechange": str(site.pk),
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

    if pyver.parse(agent.version) <= pyver.parse("0.9.5"):
        return notify_error("Only available in agent version greater than 0.9.5")

    if agent.recoveryactions.filter(last_run=None).exists():
        return notify_error(
            "A recovery action is currently pending. Please wait for the next agent check-in."
        )

    if request.data["mode"] == "command" and not request.data["cmd"]:
        return notify_error("Command is required")

    RecoveryAction(
        agent=agent,
        mode=request.data["mode"],
        command=request.data["cmd"] if request.data["mode"] == "command" else None,
    ).save()

    return Response(f"Recovery will be attempted on the agent's next check-in")


@api_view(["POST"])
def run_script(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    script = get_object_or_404(Script, pk=request.data["scriptPK"])

    output = request.data["output"]
    args = request.data["args"]

    req_timeout = int(request.data["timeout"]) + 3

    if output == "wait":
        r = agent.salt_api_cmd(
            timeout=req_timeout,
            func="win_agent.run_script",
            kwargs={
                "filepath": script.filepath,
                "filename": script.filename,
                "shell": script.shell,
                "timeout": request.data["timeout"],
                "args": args,
            },
        )

        if isinstance(r, dict):
            if r["stdout"]:
                return Response(r["stdout"])
            elif r["stderr"]:
                return Response(r["stderr"])
            else:
                try:
                    r["retcode"]
                except KeyError:
                    return notify_error("Something went wrong")

                return Response(f"Return code: {r['retcode']}")

        else:
            if r == "timeout":
                return notify_error("Unable to contact the agent")
            elif r == "error":
                return notify_error("Something went wrong")
            else:
                return notify_error(str(r))

    else:
        r = agent.salt_api_async(
            func="win_agent.run_script",
            kwargs={
                "filepath": script.filepath,
                "filename": script.filename,
                "shell": script.shell,
                "timeout": request.data["timeout"],
                "args": args,
                "bg": True,
            },
        )

        if r != "timeout":
            return Response(f"{script.name} will now be run on {agent.hostname}")
        else:
            return notify_error("Something went wrong")


@api_view()
def restart_mesh(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(func="service.restart", arg="mesh agent", timeout=30)
    if r == "timeout" or r == "error":
        return notify_error("Unable to contact the agent")
    elif isinstance(r, bool) and r:
        return Response(f"Restarted Mesh Agent on {agent.hostname}")
    else:
        return notify_error(f"Failed to restart the Mesh Agent on {agent.hostname}")


@api_view()
def recover_mesh(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    r = agent.salt_api_cmd(
        timeout=60,
        func="cmd.run",
        kwargs={
            "cmd": r'"C:\\Program Files\\TacticalAgent\\tacticalrmm.exe" -m recovermesh',
            "timeout": 55,
        },
    )
    if r == "timeout" or r == "error":
        return notify_error("Unable to contact the agent")

    return Response(f"Repaired mesh agent on {agent.hostname}")


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
