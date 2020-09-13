import os
import subprocess
from loguru import logger
from time import sleep
import random
import requests
from packaging import version as pyver


from django.conf import settings


from tacticalrmm.celery import app
from agents.models import Agent, AgentOutage

logger.configure(**settings.LOG_CONFIG)


@app.task
def send_agent_update_task(pks, version):
    assert isinstance(pks, list)
    ver = version.split("winagent-v")[1]
    q = Agent.objects.only("pk").filter(pk__in=pks)

    agents = [
        i
        for i in q
        if pyver.parse(i.version) < pyver.parse(ver) and i.status == "online"
    ]

    if agents:
        for agent in agents:
            agent.update_pending = True
            agent.save(update_fields=["update_pending"])

        minions = [i.salt_id for i in agents]

        r = Agent.get_github_versions()
        git_versions = r["versions"]
        data = r["data"]  # full response from github
        versions = {}

        for i, release in enumerate(data):
            versions[i] = release["name"]

        key = [k for k, v in versions.items() if v == version][0]

        # download_url = data[key]["assets"][1]["browser_download_url"]

        # emergency patch for now until fix tomorrow, otherwise all 64 bit agents
        # will get 32 bit agents and crash
        download_url = "https://github.com/wh1te909/winagent/releases/download/v0.11.0/winagent-v0.11.0.exe"

        # split into chunks to not overload salt
        chunks = (minions[i : i + 30] for i in range(0, len(minions), 30))

        for chunk in chunks:
            r = Agent.salt_batch_async(
                minions=chunk,
                func="win_agent.do_agent_update",
                kwargs={"version": ver, "url": download_url},
            )
            sleep(5)


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
def batch_sync_modules_task():
    # sync modules, split into chunks of 50 agents to not overload salt
    agents = Agent.objects.all()
    online = [i.salt_id for i in agents if i.status == "online"]
    chunks = (online[i : i + 50] for i in range(0, len(online), 50))
    for chunk in chunks:
        Agent.salt_batch_async(minions=chunk, func="saltutil.sync_modules")
        sleep(10)


@app.task
def batch_sysinfo_task():
    # update system info using WMI
    agents = Agent.objects.all()
    online = [
        i.salt_id
        for i in agents
        if not i.not_supported("0.11.0") and i.status == "online"
    ]
    chunks = (online[i : i + 30] for i in range(0, len(online), 30))
    for chunk in chunks:
        Agent.salt_batch_async(minions=chunk, func="win_agent.local_sys_info")
        sleep(10)


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
    sleep(random.randint(1, 15))
    outage = AgentOutage.objects.get(pk=pk)
    outage.send_outage_email()
    outage.outage_email_sent = True
    outage.save(update_fields=["outage_email_sent"])


@app.task
def agent_recovery_email_task(pk):
    sleep(random.randint(1, 15))
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
