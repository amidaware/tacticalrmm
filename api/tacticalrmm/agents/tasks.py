from loguru import logger
from time import sleep
import random
import requests
from packaging import version as pyver


from django.conf import settings


from tacticalrmm.celery import app
from agents.models import Agent, AgentOutage
from core.models import CoreSettings

logger.configure(**settings.LOG_CONFIG)

OLD_64_PY_AGENT = "https://github.com/wh1te909/winagent/releases/download/v0.11.2/winagent-v0.11.2.exe"
OLD_32_PY_AGENT = "https://github.com/wh1te909/winagent/releases/download/v0.11.2/winagent-v0.11.2-x86.exe"


@app.task
def send_agent_update_task(pks, version):
    assert isinstance(pks, list)

    q = Agent.objects.filter(pk__in=pks)
    agents = [i.pk for i in q if pyver.parse(i.version) < pyver.parse(version)]

    chunks = (agents[i : i + 30] for i in range(0, len(agents), 30))

    for chunk in chunks:
        for pk in chunk:
            agent = Agent.objects.get(pk=pk)

            # skip if we can't determine the arch
            if agent.arch is None:
                logger.warning(
                    f"Unable to determine arch on {agent.salt_id}. Skipping."
                )
                continue

            # golang agent only backwards compatible with py agent 0.11.2
            # force an upgrade to the latest python agent if version < 0.11.2
            if pyver.parse(agent.version) < pyver.parse("0.11.2"):
                url = OLD_64_PY_AGENT if agent.arch == "64" else OLD_32_PY_AGENT
                inno = (
                    "winagent-v0.11.2.exe"
                    if agent.arch == "64"
                    else "winagent-v0.11.2-x86.exe"
                )
            else:
                url = agent.winagent_dl
                inno = agent.win_inno_exe
            logger.info(
                f"Updating {agent.salt_id} current version {agent.version} using {inno}"
            )
            r = agent.salt_api_async(
                func="win_agent.do_agent_update_v2",
                kwargs={
                    "inno": inno,
                    "url": url,
                },
            )
            logger.info(f"{agent.salt_id}: {r}")
        sleep(10)


@app.task
def auto_self_agent_update_task():
    core = CoreSettings.objects.first()
    if not core.agent_auto_update:
        logger.info("Agent auto update is disabled. Skipping.")
        return

    q = Agent.objects.only("pk", "version")
    agents = [
        i.pk
        for i in q
        if pyver.parse(i.version) < pyver.parse(settings.LATEST_AGENT_VER)
    ]
    logger.info(f"Updating {len(agents)}")

    chunks = (agents[i : i + 30] for i in range(0, len(agents), 30))

    for chunk in chunks:
        for pk in chunk:
            agent = Agent.objects.get(pk=pk)

            # skip if we can't determine the arch
            if agent.arch is None:
                logger.warning(
                    f"Unable to determine arch on {agent.salt_id}. Skipping."
                )
                continue

            # golang agent only backwards compatible with py agent 0.11.2
            # force an upgrade to the latest python agent if version < 0.11.2
            if pyver.parse(agent.version) < pyver.parse("0.11.2"):
                url = OLD_64_PY_AGENT if agent.arch == "64" else OLD_32_PY_AGENT
                inno = (
                    "winagent-v0.11.2.exe"
                    if agent.arch == "64"
                    else "winagent-v0.11.2-x86.exe"
                )
            else:
                url = agent.winagent_dl
                inno = agent.win_inno_exe
            logger.info(
                f"Updating {agent.salt_id} current version {agent.version} using {inno}"
            )
            r = agent.salt_api_async(
                func="win_agent.do_agent_update_v2",
                kwargs={
                    "inno": inno,
                    "url": url,
                },
            )
            logger.info(f"{agent.salt_id}: {r}")
        sleep(10)


@app.task
def update_salt_minion_task():
    q = Agent.objects.all()
    agents = [
        i.pk
        for i in q
        if pyver.parse(i.version) >= pyver.parse("0.11.0")
        and pyver.parse(i.salt_ver) < pyver.parse(settings.LATEST_SALT_VER)
    ]

    chunks = (agents[i : i + 50] for i in range(0, len(agents), 50))

    for chunk in chunks:
        for pk in chunk:
            agent = Agent.objects.get(pk=pk)
            r = agent.salt_api_async(func="win_agent.update_salt")
        sleep(20)


@app.task
def get_wmi_detail_task(pk):
    agent = Agent.objects.get(pk=pk)
    r = agent.salt_api_async(timeout=30, func="win_agent.local_sys_info")
    return "ok"


@app.task
def sync_salt_modules_task(pk):
    agent = Agent.objects.get(pk=pk)
    r = agent.salt_api_cmd(timeout=35, func="saltutil.sync_modules")
    # successful sync if new/charnged files: {'return': [{'MINION-15': ['modules.get_eventlog', 'modules.win_agent', 'etc...']}]}
    # successful sync with no new/changed files: {'return': [{'MINION-15': []}]}
    if r == "timeout" or r == "error":
        return f"Unable to sync modules {agent.salt_id}"

    return f"Successfully synced salt modules on {agent.hostname}"


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
def agent_outage_sms_task(pk):
    sleep(random.randint(1, 3))
    outage = AgentOutage.objects.get(pk=pk)
    outage.send_outage_sms()
    outage.outage_sms_sent = True
    outage.save(update_fields=["outage_sms_sent"])


@app.task
def agent_recovery_sms_task(pk):
    sleep(random.randint(1, 3))
    outage = AgentOutage.objects.get(pk=pk)
    outage.send_recovery_sms()
    outage.recovery_sms_sent = True
    outage.save(update_fields=["recovery_sms_sent"])


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

            if agent.overdue_email_alert and not agent.maintenance_mode:
                agent_outage_email_task.delay(pk=outage.pk)

            if agent.overdue_text_alert and not agent.maintenance_mode:
                agent_outage_sms_task.delay(pk=outage.pk)
