import datetime
from datetime import timezone
from statistics import mean

from tacticalrmm.celery import app
from django.core.exceptions import ObjectDoesNotExist

from agents.models import Agent
from clients.models import Client, Site
from .models import (
    DiskCheck,
    DiskCheckEmail,
    PingCheck,
    PingCheckEmail,
    CpuLoadCheck,
    CpuLoadCheckEmail,
    MemCheck,
    MemCheckEmail,
    WinServiceCheck,
    WinServiceCheckEmail,
    ScriptCheck,
    ScriptCheckEmail,
)


@app.task
def handle_check_email_alert_task(check_type, pk):
    if check_type == "ping":
        check = PingCheck.objects.get(pk=pk)
        eml = PingCheckEmail
    elif check_type == "diskspace":
        check = DiskCheck.objects.get(pk=pk)
        eml = DiskCheckEmail
    elif check_type == "cpuload":
        check = CpuLoadCheck.objects.get(pk=pk)
        eml = CpuLoadCheckEmail
    elif check_type == "memory":
        check = MemCheck.objects.get(pk=pk)
        eml = MemCheckEmail
    elif check_type == "winsvc":
        check = WinServiceCheck.objects.get(pk=pk)
        eml = WinServiceCheckEmail
    elif check_type == "script":
        check = ScriptCheck.objects.get(pk=pk)
        eml = ScriptCheckEmail
    else:
        return {"error": "no check"}

    try:
        latest_email = eml.objects.filter(email=check).order_by("-sent")[:1].get()
    except:
        # first time sending email
        eml(email=check).save()
        check.send_email()
    else:
        last_sent = latest_email.sent
        delta = datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=24)
        # send an email only if the last email sent is older than 24 hours
        if last_sent < delta:
            eml(email=check).save()
            check.send_email()

    return "ok"


@app.task
def checks_failing_task():
    diskchecks = DiskCheck.objects.select_related("agent").only(
        "agent__client", "agent__site", "status"
    )
    pingchecks = PingCheck.objects.select_related("agent").only(
        "agent__client", "agent__site", "status"
    )
    cpuloadchecks = CpuLoadCheck.objects.select_related("agent").only(
        "agent__client", "agent__site", "status"
    )
    memchecks = MemCheck.objects.select_related("agent").only(
        "agent__client", "agent__site", "status"
    )
    winservicechecks = WinServiceCheck.objects.select_related("agent").only(
        "agent__client", "agent__site", "status"
    )
    scriptchecks = ScriptCheck.objects.select_related("agent").only(
        "agent__client", "agent__site", "status"
    )

    agents_failing = []

    for check in (
        diskchecks,
        pingchecks,
        cpuloadchecks,
        memchecks,
        winservicechecks,
        scriptchecks,
    ):
        for i in check:
            if i.status == "failing":
                agents_failing.append(i.agent.pk)

    agents_failing = list(set(agents_failing))  # remove duplicates

    # first we reset all to passing
    Client.objects.all().update(checks_failing=False)
    Site.objects.all().update(checks_failing=False)

    # then update only those that are failing
    if agents_failing:
        for pk in agents_failing:
            agent = Agent.objects.get(pk=pk)
            client = Client.objects.get(client=agent.client)
            site = Site.objects.filter(client=client).get(site=agent.site)

            client.checks_failing = True
            site.checks_failing = True
            client.save(update_fields=["checks_failing"])
            site.save(update_fields=["checks_failing"])

    return "ok"


@app.task
def restart_win_service_task(pk, svcname):
    agent = Agent.objects.get(pk=pk)
    resp = agent.salt_api_cmd(
        hostname=agent.salt_id, timeout=60, func=f"service.restart", arg=svcname,
    )
    data = resp.json()
    if not data["return"][0][agent.salt_id]:
        return {"error": f"restart service {svcname} failed on {agent.hostname}"}
    return "ok"


@app.task
def run_checks_task(pk):
    agent = Agent.objects.get(pk=pk)
    try:
        agent.salt_api_async(hostname=agent.salt_id, func="win_agent.run_manual_checks")
    except:
        pass

    return "ok"
