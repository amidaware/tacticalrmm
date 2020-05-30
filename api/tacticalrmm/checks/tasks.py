import datetime as dt

from tacticalrmm.celery import app
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone as djangotime

from agents.models import Agent
from clients.models import Client, Site


@app.task
def handle_check_email_alert_task(pk):
    from .models import Check

    check = Check.objects.get(pk=pk)

    # first time sending email
    if not check.email_sent:
        check.send_email()
        check.email_sent = djangotime.now()
        check.save(update_fields=["email_sent"])
    else:
        # send an email only if the last email sent is older than 24 hours
        delta = djangotime.now() - dt.timedelta(hours=24)
        if check.email_sent < delta:
            check.send_email()
            check.email_sent = djangotime.now()
            check.save(update_fields=["email_sent"])

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
