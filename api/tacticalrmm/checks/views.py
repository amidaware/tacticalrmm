import validators
import datetime as dt

from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime

from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from agents.models import Agent

from .models import (
    DiskCheck,
    PingCheck,
    PingCheckEmail,
    CpuLoadCheck,
    MemCheck,
    WinServiceCheck,
    Script,
    ScriptCheck,
    ScriptCheckEmail,
    validate_threshold,
)

from .serializers import (
    CheckSerializer,
    DiskCheckSerializer,
    PingCheckSerializer,
    CpuLoadCheckSerializer,
    MemCheckSerializer,
    WinServiceCheckSerializer,
    ScriptCheckSerializer,
    ScriptSerializer,
)

from .tasks import handle_check_email_alert_task, run_checks_task


@api_view()
def get_scripts(request):
    scripts = Script.objects.all()
    return Response(ScriptSerializer(scripts, many=True, read_only=True).data)


@api_view()
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def check_runner(request):
    agent = get_object_or_404(Agent, agent_id=request.data["agent_id"])
    return Response(CheckSerializer(agent).data)


@api_view(["PATCH"])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def update_check(request):
    if request.data["check_type"] == "diskspace":
        check = get_object_or_404(DiskCheck, pk=request.data["id"])
        check.last_run = dt.datetime.now(tz=djangotime.utc)
        check.save(update_fields=["last_run"])
        serializer = DiskCheckSerializer(
            instance=check, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        check.handle_check(request.data)

    elif request.data["check_type"] == "cpuload":
        check = get_object_or_404(CpuLoadCheck, pk=request.data["id"])
        check.handle_check(request.data)

    elif request.data["check_type"] == "memory":
        check = get_object_or_404(MemCheck, pk=request.data["id"])
        check.handle_check(request.data)

    elif request.data["check_type"] == "winsvc":
        check = get_object_or_404(WinServiceCheck, pk=request.data["id"])
        check.last_run = dt.datetime.now(tz=djangotime.utc)
        check.save(update_fields=["last_run"])
        serializer = WinServiceCheckSerializer(
            instance=check, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        check.handle_check(request.data)

    elif request.data["check_type"] == "script":
        check = get_object_or_404(ScriptCheck, pk=request.data["id"])
        check.last_run = dt.datetime.now(tz=djangotime.utc)
        check.save(update_fields=["last_run"])
        serializer = ScriptCheckSerializer(
            instance=check, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        check.handle_check(request.data)

    elif request.data["check_type"] == "ping":
        check = get_object_or_404(PingCheck, pk=request.data["id"])
        check.last_run = dt.datetime.now(tz=djangotime.utc)
        check.save(update_fields=["last_run"])
        serializer = PingCheckSerializer(
            instance=check, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        check.handle_check(request.data)

    else:
        return Response("error", status=status.HTTP_400_BAD_REQUEST)

    return Response("ok")


@api_view()
def run_checks(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    run_checks_task.delay(agent.pk)
    return Response(agent.hostname)


@api_view()
def load_checks(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    return Response(CheckSerializer(agent).data)


@api_view()
def get_disks(request, pk):
    return Response(get_object_or_404(Agent, pk=pk).disks)


@api_view(["POST"])
def add_standard_check(request):
    agent = get_object_or_404(Agent, pk=request.data["pk"])
    if request.data["check_type"] == "diskspace":
        disk = request.data["disk"]
        threshold = request.data["threshold"]
        failures = request.data["failure"]
        existing_checks = DiskCheck.objects.filter(agent=agent)
        if existing_checks:
            for check in existing_checks:
                if disk in check.disk:
                    error = {"error": f"A disk check for drive {disk} already exists!"}
                    return Response(error, status=status.HTTP_400_BAD_REQUEST)

        if not validate_threshold(threshold):
            error = {"error": "Please enter a valid threshold between 1 and 99"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        DiskCheck(agent=agent, disk=disk, threshold=threshold, failures=failures).save()
        return Response("ok")

    elif request.data["check_type"] == "ping":
        failures = request.data["failures"]
        name = request.data["name"]
        ip = request.data["ip"]
        if not PingCheck.validate_hostname_or_ip(ip):
            error = {"error": "Please enter a valid hostname or IP"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        PingCheck(agent=agent, ip=ip, name=name, failures=failures).save()
        return Response("ok")

    elif request.data["check_type"] == "cpuload":
        if CpuLoadCheck.objects.filter(agent=agent):
            error = {"error": f"A cpu load check for {agent.hostname} already exists!"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        threshold = request.data["threshold"]
        failures = request.data["failure"]
        if not validate_threshold(threshold):
            error = {"error": "Please enter a valid threshold between 1 and 99"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        CpuLoadCheck(agent=agent, cpuload=threshold, failures=failures).save()
        return Response("ok")

    elif request.data["check_type"] == "mem":
        if MemCheck.objects.filter(agent=agent):
            error = {"error": f"A memory check for {agent.hostname} already exists!"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        threshold = request.data["threshold"]
        failures = request.data["failure"]
        if not validate_threshold(threshold):
            error = {"error": "Please enter a valid threshold between 1 and 99"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        MemCheck(agent=agent, threshold=threshold, failures=failures).save()
        return Response("ok")

    elif request.data["check_type"] == "winsvc":
        displayName = request.data["displayname"]
        rawName = request.data["rawname"]
        pass_start_pending = request.data["passifstartpending"]
        restart_stopped = request.data["restartifstopped"]
        failures = request.data["failures"]

        existing_checks = WinServiceCheck.objects.filter(agent=agent)
        if existing_checks:
            for check in existing_checks:
                if rawName in check.svc_name:
                    error = {
                        "error": f"There is already a check for service {check.svc_display_name}"
                    }
                    return Response(error, status=status.HTTP_400_BAD_REQUEST)

        WinServiceCheck(
            agent=agent,
            svc_name=rawName,
            svc_display_name=displayName,
            pass_if_start_pending=pass_start_pending,
            restart_if_stopped=restart_stopped,
            failures=failures,
        ).save()
        return Response("ok")

    elif request.data["check_type"] == "script":
        script_pk = request.data["scriptPk"]
        timeout = request.data["timeout"]
        failures = request.data["failures"]

        script = Script.objects.get(pk=script_pk)

        if ScriptCheck.objects.filter(agent=agent).filter(script=script).exists():
            return Response(
                f"{script.name} already exists on {agent.hostname}",
                status=status.HTTP_400_BAD_REQUEST,
            )

        ScriptCheck(
            agent=agent, timeout=timeout, failures=failures, script=script
        ).save()

        return Response(f"{script.name} was added on {agent.hostname}!")

    else:
        return Response("something went wrong", status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH"])
def edit_standard_check(request):
    if request.data["check_type"] == "diskspace":
        check = get_object_or_404(DiskCheck, pk=request.data["pk"])
        if not validate_threshold(request.data["threshold"]):
            error = {"error": "Please enter a valid threshold between 1 and 99"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        check.threshold = request.data["threshold"]
        check.failures = request.data["failures"]
        check.save(update_fields=["threshold", "failures"])
        return Response("ok")

    elif request.data["check_type"] == "ping":
        check = get_object_or_404(PingCheck, pk=request.data["pk"])
        if not PingCheck.validate_hostname_or_ip(request.data["ip"]):
            error = {"error": "Please enter a valid hostname or IP"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        check.name = request.data["name"]
        check.ip = request.data["ip"]
        check.failures = request.data["failures"]
        check.save(update_fields=["name", "ip", "failures"])
        return Response("ok")

    elif request.data["check_type"] == "cpuload":
        check = get_object_or_404(CpuLoadCheck, pk=request.data["pk"])
        if not validate_threshold(request.data["threshold"]):
            error = {"error": "Please enter a valid threshold between 1 and 99"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        check.cpuload = request.data["threshold"]
        check.failures = request.data["failure"]
        check.save(update_fields=["cpuload", "failures"])
        return Response("ok")

    elif request.data["check_type"] == "mem":
        check = get_object_or_404(MemCheck, pk=request.data["pk"])
        if not validate_threshold(request.data["threshold"]):
            error = {"error": "Please enter a valid threshold between 1 and 99"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        check.threshold = request.data["threshold"]
        check.failures = request.data["failure"]
        check.save(update_fields=["threshold", "failures"])
        return Response("ok")

    elif request.data["check_type"] == "winsvc":
        check = get_object_or_404(WinServiceCheck, pk=request.data["pk"])
        check.pass_if_start_pending = request.data["passifstartpending"]
        check.restart_if_stopped = request.data["restartifstopped"]
        check.failures = request.data["failures"]
        check.save(
            update_fields=["pass_if_start_pending", "restart_if_stopped", "failures"]
        )
        return Response("ok")

    elif request.data["check_type"] == "script":
        check = get_object_or_404(ScriptCheck, pk=request.data["pk"])
        check.failures = request.data["failures"]
        check.timeout = request.data["timeout"]
        check.save(update_fields=["failures", "timeout"])
        return Response(f"{check.script.name} was edited on {check.agent.hostname}")


@api_view()
def get_standard_check(request, checktype, pk):
    if checktype == "diskspace":
        check = DiskCheck.objects.get(pk=pk)
        return Response(DiskCheckSerializer(check).data)
    elif checktype == "ping":
        check = PingCheck.objects.get(pk=pk)
        return Response(PingCheckSerializer(check).data)
    elif checktype == "cpuload":
        check = CpuLoadCheck.objects.get(pk=pk)
        return Response(CpuLoadCheckSerializer(check).data)
    elif checktype == "mem":
        check = MemCheck.objects.get(pk=pk)
        return Response(MemCheckSerializer(check).data)
    elif checktype == "winsvc":
        check = WinServiceCheck.objects.get(pk=pk)
        return Response(WinServiceCheckSerializer(check).data)
    elif checktype == "script":
        check = ScriptCheck.objects.get(pk=pk)
        return Response(ScriptCheckSerializer(check).data)


@api_view(["DELETE"])
def delete_standard_check(request):
    pk = request.data["pk"]
    if request.data["checktype"] == "diskspace":
        check = DiskCheck.objects.get(pk=pk)
    elif request.data["checktype"] == "ping":
        check = PingCheck.objects.get(pk=pk)
    elif request.data["checktype"] == "cpuload":
        check = CpuLoadCheck.objects.get(pk=pk)
    elif request.data["checktype"] == "memory":
        check = MemCheck.objects.get(pk=pk)
    elif request.data["checktype"] == "winsvc":
        check = WinServiceCheck.objects.get(pk=pk)
    elif request.data["checktype"] == "script":
        check = ScriptCheck.objects.get(pk=pk)

    check.delete()
    return Response("ok")


@api_view(["PATCH"])
def check_alert(request):
    alert_type = request.data["alertType"]
    category = request.data["category"]
    checkid = request.data["checkid"]
    action = request.data["action"]
    if category == "diskspace":
        check = DiskCheck.objects.get(pk=checkid)
    elif category == "cpuload":
        check = CpuLoadCheck.objects.get(pk=checkid)
    elif category == "memory":
        check = MemCheck.objects.get(pk=checkid)
    elif category == "ping":
        check = PingCheck.objects.get(pk=checkid)
    elif category == "winsvc":
        check = WinServiceCheck.objects.get(pk=checkid)
    elif category == "script":
        check = ScriptCheck.objects.get(pk=checkid)
    else:
        return Response(
            {"error": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST
        )

    if alert_type == "email" and action == "enabled":
        check.email_alert = True
        check.save(update_fields=["email_alert"])
    elif alert_type == "email" and action == "disabled":
        check.email_alert = False
        check.save(update_fields=["email_alert"])
    elif alert_type == "text" and action == "enabled":
        check.text_alert = True
        check.save(update_fields=["text_alert"])
    elif alert_type == "text" and action == "disabled":
        check.text_alert = False
        check.save(update_fields=["text_alert"])
    else:
        return Response(
            {"error": "Something terrible went wrong"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response("ok")
