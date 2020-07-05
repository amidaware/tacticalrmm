import os
import subprocess
from loguru import logger
from time import sleep
import requests


from django.conf import settings


from tacticalrmm.celery import app
from agents.models import Agent, AgentOutage

logger.configure(**settings.LOG_CONFIG)


@app.task
def get_wmi_detail_task(pk):
    agent = Agent.objects.get(pk=pk)
    r = agent.salt_api_cmd(timeout=30, func="win_agent.system_info")
    if r == "timeout" or r == "error":
        return "failed"

    agent.wmi_detail = r
    agent.save(update_fields=["wmi_detail"])
    return "ok"


@app.task
def sync_salt_modules_task(pk):
    agent = Agent.objects.get(pk=pk)
    r = agent.salt_api_cmd(timeout=35, func="saltutil.sync_modules")
    # successful sync if new/charnged files: {'return': [{'MINION-15': ['modules.get_eventlog', 'modules.win_agent', 'etc...']}]}
    # successful sync with no new/changed files: {'return': [{'MINION-15': []}]}
    if r == "timeout" or r == "error":
        logger.error(f"Unable to sync modules {agent.salt_id}")
        return

    logger.info(f"Successfully synced salt modules on {agent.hostname}")
    return "ok"


@app.task
def uninstall_agent_task(salt_id):
    attempts = 0
    error = False

    while 1:
        try:

            r = requests.post(
                f"http://{settings.SALT_HOST}:8123/run",
                json=[
                    {
                        "client": "local",
                        "tgt": salt_id,
                        "fun": "win_agent.uninstall_agent",
                        "timeout": 8,
                        "username": settings.SALT_USERNAME,
                        "password": settings.SALT_PASSWORD,
                        "eauth": "pam",
                    }
                ],
                timeout=10,
            )
            ret = r.json()["return"][0][salt_id]
        except Exception:
            attempts += 1
        else:
            if ret != "ok":
                attempts += 1
            else:
                attempts = 0

        if attempts >= 10:
            error = True
            break
        elif attempts == 0:
            break

    if error:
        logger.error(f"{salt_id} uninstall failed")
    else:
        logger.info(f"{salt_id} was successfully uninstalled")

    try:
        r = requests.post(
            f"http://{settings.SALT_HOST}:8123/run",
            json=[
                {
                    "client": "wheel",
                    "fun": "key.delete",
                    "match": salt_id,
                    "username": settings.SALT_USERNAME,
                    "password": settings.SALT_PASSWORD,
                    "eauth": "pam",
                }
            ],
            timeout=30,
        )
    except Exception:
        logger.error(f"{salt_id} unable to remove salt-key")

    return "ok"


@app.task
def agent_outage_email_task(pk):
    outage = AgentOutage.objects.get(pk=pk)
    outage.send_outage_email()
    outage.outage_email_sent = True
    outage.save(update_fields=["outage_email_sent"])


@app.task
def agent_recovery_email_task(pk):
    outage = AgentOutage.objects.get(pk=pk)
    outage.send_recovery_email()
    outage.recovery_email_sent = True
    outage.save(update_fields=["recovery_email_sent"])


@app.task
def agent_outages_task():
    agents = Agent.objects.only("pk")

    for agent in agents:
        if agent.status == "overdue":
            outages = AgentOutage.objects.filter(agent=agent)
            if outages and outages.last().is_active:
                continue

            outage = AgentOutage(agent=agent)
            outage.save()

            if agent.overdue_email_alert:
                agent_outage_email_task.delay(pk=outage.pk)

            if agent.overdue_text_alert:
                # TODO
                pass
