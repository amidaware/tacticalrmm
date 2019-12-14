from pymongo import MongoClient
import requests
from subprocess import run, PIPE
import os
import distro
from time import sleep
from loguru import logger

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ParseError
from rest_framework.parsers import FileUploadParser
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.authentication import (
    BasicAuthentication,
    TokenAuthentication,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from agents.models import Agent
from accounts.models import User
from checks.models import (
    DiskCheck,
    CpuLoadCheck,
    MemCheck,
    PingCheck,
    MemoryHistory,
    CpuHistory,
)
from winupdate.models import WinUpdate, WinUpdatePolicy
from agents.tasks import uninstall_agent_task, sync_salt_modules_task
from winupdate.tasks import check_for_updates_task
from agents.serializers import AgentHostnameSerializer

logger.configure(**settings.LOG_CONFIG)

class UploadMeshAgent(APIView):
    parser_class = (FileUploadParser,)

    def put(self, request, format=None):
        if 'meshagent' not in request.data:
            raise ParseError("Empty content")

        f = request.data['meshagent']
        mesh_exe = os.path.join(settings.BASE_DIR, "tacticalrmm/downloads/meshagent.exe")
        with open(mesh_exe, "wb+") as j:
            for chunk in f.chunks():
                j.write(chunk)

        return Response(status=status.HTTP_201_CREATED)

@api_view(["PATCH"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def trigger_patch_scan(request):
    agent = get_object_or_404(Agent, agent_id=request.data["agentid"])
    check_for_updates_task.delay(agent.pk)

    if request.data["reboot"]:
        agent.needs_reboot = True
    else:
        agent.needs_reboot = False
        
    agent.save(update_fields=["needs_reboot"])
    return Response("ok")

@api_view()
def download_log(request):
    log_file = os.path.join(settings.BASE_DIR, "log/debug.log")
    if settings.DEBUG:
        with open(log_file, "rb") as f:
            response = HttpResponse(f.read(), content_type="text/plain")
            response["Content-Disposition"] = "attachment; filename=debug.log"
            return response
    else:
        response = HttpResponse()
        response["Content-Disposition"] = "attachment; filename=debug.log"
        response['X-Accel-Redirect'] = "/protectedlogs/debug.log"
        return response

@api_view()
def get_log(request, mode, hostname, order):
    log_file = os.path.join(settings.BASE_DIR, "log/debug.log")

    agents = Agent.objects.all()
    agent_hostnames = AgentHostnameSerializer(agents, many=True)

    dist = distro.linux_distribution(full_distribution_name=False)[0]
    switch_grep = {"centos": "/usr/bin/grep", "ubuntu": "/bin/grep", "debian": "/usr/bin/grep"}
    grep = switch_grep.get(dist, "/bin/grep")
    tac = "/usr/bin/tac"
    
    switch_mode = {"info": "INFO", "critical": "CRITICAL", "error": "ERROR", "warning": "WARNING"}
    level = switch_mode.get(mode, "INFO")

    if hostname == "all" and order == "latest":
        cmd = f"{grep} -h {level} {log_file} | {tac}"
    elif hostname == "all" and order == "oldest":
        cmd = f"{grep} -h {level} {log_file}"
    elif hostname != "all" and order == "latest":
        cmd = f"{grep} {hostname} {log_file} | {grep} -h {level} | {tac}"
    elif hostname != "all" and order == "oldest":
        cmd = f"{grep} {hostname} {log_file} | {grep} -h {level}"
    else:
        return Response("error", status=status.HTTP_400_BAD_REQUEST)
        
    contents = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)

    if not contents.stdout:
        resp = f"Hooray! No {mode} logs!"
    else:
        resp = contents.stdout

    return Response({"log": resp, "agents": agent_hostnames.data})

@api_view(["POST"])
@authentication_classes((BasicAuthentication,))
@permission_classes((IsAuthenticated,))
# installer auth
def agent_auth(request):
    return Response("ok")


@api_view(["POST"])
@authentication_classes((BasicAuthentication,))
@permission_classes((IsAuthenticated,))
def get_mesh_exe(request):
    if settings.DEBUG:
        mesh_exe = os.path.join(settings.BASE_DIR, "tacticalrmm/downloads/meshagent.exe")
        with open(mesh_exe, "rb") as f:
            response = HttpResponse(
                f.read(), content_type="application/vnd.microsoft.portable-executable"
            )
            response["Content-Disposition"] = "inline; filename=meshagent.exe"
            return response
    else:
        response = HttpResponse()
        response["Content-Disposition"] = "attachment; filename=meshagent.exe"
        response['X-Accel-Redirect'] = "/protected/meshagent.exe"
        return response


@api_view()
@authentication_classes((BasicAuthentication,))
@permission_classes((IsAuthenticated,))
# installer get list of nodes from meshcentral database
def get_mesh_nodes(request):
    client = MongoClient('localhost', 27017)
    db = client.meshcentral
    cursor = db.meshcentral.find({"type": "node"})
    nodes = {}
    for i in cursor:
        nodes[i['rname']] = i['_id'].replace('node//', '')
    return Response(nodes)

@api_view(["POST"])
@authentication_classes((BasicAuthentication,))
@permission_classes((IsAuthenticated,))
def create_auth_token(request):
    try:
        agentid = request.data["agentid"]
    except Exception:
        logger.error("agentid was not provided with request")
        return Response({"error": "bad data"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        try:
            user = User.objects.create_user(username=agentid, password=User.objects.make_random_password(50))
        except IntegrityError:
            user = User.objects.get(username=agentid)
            token = Token.objects.get(user=user)
            return Response({"token": token.key})

    try:
        user = User.objects.get(username=agentid)
    except Exception:
        return Response({"error": "bad user"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        token = Token.objects.create(user=user)
        return Response({"token": token.key})

@api_view(["POST"])
@authentication_classes((BasicAuthentication,))
@permission_classes((IsAuthenticated,))
def accept_salt_key(request, hostname):
    try:
        resp = requests.post(
            "http://localhost:8123/run",
            json=[
                {
                    "client": "wheel",
                    "fun": "key.accept",
                    "match": hostname,
                    "username": settings.SALT_USERNAME,
                    "password": settings.SALT_PASSWORD,
                    "eauth": "pam",
                }
            ],
            timeout=30,
        )
    except requests.exceptions.Timeout:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    except requests.exceptions.ConnectionError:
        return Response(status=status.HTTP_410_GONE)
    return Response("ok")

@api_view(["POST"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def delete_agent(request):
    try:
        user = User.objects.get(username=request.data["agentid"])
        agent = Agent.objects.get(agent_id=request.data["agentid"])
        user.delete()
        agent.delete()
    except Exception as e:
        logger.error(e)
        return Response({"error": "something went wrong"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        err = "Error removing agent from salt master. Please manually remove."
        try:
            resp = requests.post(
                "http://localhost:8123/run",
                json=[
                    {
                        "client": "wheel",
                        "fun": "key.delete",
                        "match": agent.hostname,
                        "username": settings.SALT_USERNAME,
                        "password": settings.SALT_PASSWORD,
                        "eauth": "pam",
                    }
                ],
                timeout=30,
            )
        except requests.exceptions.Timeout:
            return Response(err, status=status.HTTP_400_BAD_REQUEST)
        except requests.exceptions.ConnectionError:
            return Response(err, status=status.HTTP_410_GONE)
        return Response("ok")


@api_view(["POST"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def add(request):
    data = request.data
    agent_id = data["agentid"]
    hostname = data["hostname"]
    client = data["client"]
    site = data["site"]
    monitoring_type = data["monitoring_type"]
    description = data["description"]
    mesh_node_id = data["mesh_node_id"]

    if not Agent.objects.filter(agent_id=agent_id).exists():
        Agent(
            agent_id=agent_id,
            hostname=hostname,
            client=client,
            site=site,
            monitoring_type=monitoring_type,
            description=description,
            mesh_node_id=mesh_node_id,
        ).save()

        agent = Agent.objects.get(agent_id=agent_id)
        MemoryHistory(agent=agent).save()
        CpuHistory(agent=agent).save()

        if agent.monitoring_type == "workstation":
            WinUpdatePolicy(agent=agent, run_time_days=[5, 6]).save()
        else:
            WinUpdatePolicy(agent=agent).save()

    
    return Response("ok")


@api_view(["PATCH"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def update(request):
    data = request.data
    agent_id = data["agentid"]
    hostname = data["hostname"]
    os = data["operating_system"]
    total_ram = data["total_ram"]
    cpu_info = data["cpu_info"]
    plat = data["platform"]
    plat_release = data["platform_release"]
    version = data["version"]
    av = data["av"]

    agent = get_object_or_404(Agent, agent_id=agent_id)

    agent.hostname = hostname
    agent.operating_system = os
    agent.total_ram = total_ram
    agent.cpu_info = cpu_info
    agent.plat = plat
    agent.plat_release = plat_release
    agent.version = version
    agent.antivirus = av

    agent.save(update_fields=[
        "last_seen",
        "hostname",
        "operating_system",
        "total_ram",
        "cpu_info",
        "plat",
        "plat_release",
        "version",
        "antivirus",
    ])

    sync_salt_modules_task.delay(agent.pk)

    # check for updates if this is fresh agent install
    if not WinUpdate.objects.filter(agent=agent).exists():
        check_for_updates_task.delay(agent.pk)


    return Response("ok")


@api_view(["PATCH"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def hello(request):
    data = request.data
    agent_id = data["agentid"]
    local_ip = data["local_ip"]
    services = data["services"]
    public_ip = data["public_ip"]
    cpu_load = data["cpu_load"]
    used_ram = data["used_ram"]
    disks = data["disks"]
    boot_time = data["boot_time"]
    logged_in_username = data["logged_in_username"]
    
    agent = get_object_or_404(Agent, agent_id=agent_id)

    if agent.uninstall_pending:
        if agent.uninstall_inprogress:
            return Response("uninstallip")
        else:
            uninstall_agent_task.delay(agent.pk)
            return Response("ok")

    
    agent.local_ip = local_ip
    agent.public_ip = public_ip
    agent.services = services
    agent.cpu_load = cpu_load
    
    agent.used_ram = used_ram
    agent.disks = disks
    agent.boot_time = boot_time
    agent.logged_in_username = logged_in_username
    
    agent.save(
        update_fields=[
            "last_seen",
            "local_ip",
            "public_ip",
            "services",
            "cpu_load",
            "used_ram",
            "disks",
            "boot_time",
            "logged_in_username", 
        ]
    )

    # create a list of the last 35 mem averages
    mem = MemoryHistory.objects.get(agent=agent)
    mem_list = mem.mem_history

    if len(mem_list) < 35:
        mem_list.append(used_ram)
        mem.mem_history = mem_list
        mem.save(update_fields=["mem_history"])
    else:
        mem_list.append(used_ram)
        new_mem_list = mem_list[-35:]
        mem.mem_history = new_mem_list
        mem.save(update_fields=["mem_history"])

    # create list of the last 35 cpu load averages
    cpu = CpuHistory.objects.get(agent=agent)
    cpu_list = cpu.cpu_history

    if len(cpu_list) < 35:
        cpu_list.append(cpu_load)
        cpu.cpu_history = cpu_list
        cpu.save(update_fields=["cpu_history"])
    else:
        cpu_list.append(cpu_load)
        new_cpu_list = cpu_list[-35:]
        cpu.cpu_history = new_cpu_list
        cpu.save(update_fields=["cpu_history"])
    
    return Response("ok")