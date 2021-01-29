import asyncio
from loguru import logger
from time import sleep
import random
from packaging import version as pyver
from typing import List

from django.conf import settings
from scripts.models import Script

from tacticalrmm.celery import app
from agents.models import Agent, AgentOutage
from core.models import CoreSettings
from logs.models import PendingAction

logger.configure(**settings.LOG_CONFIG)


def _check_agent_service(pk: int) -> None:
    agent = Agent.objects.get(pk=pk)
    r = asyncio.run(agent.nats_cmd({"func": "ping"}, timeout=2))
    # if the agent is respoding to pong from the rpc service but is not showing as online (handled by tacticalagent service)
    # then tacticalagent service is hung. forcefully restart it
    if r == "pong":
        logger.info(
            f"Detected crashed tacticalagent service on {agent.hostname} v{agent.version}, attempting recovery"
        )
        data = {"func": "recover", "payload": {"mode": "tacagent"}}
        asyncio.run(agent.nats_cmd(data, wait=False))


def _check_in_full(pk: int) -> None:
    agent = Agent.objects.get(pk=pk)
    asyncio.run(agent.nats_cmd({"func": "checkinfull"}, wait=False))


@app.task
def check_in_task() -> None:
    q = Agent.objects.only("pk", "version")
    agents: List[int] = [
        i.pk for i in q if pyver.parse(i.version) == pyver.parse("1.1.12")
    ]
    chunks = (agents[i : i + 50] for i in range(0, len(agents), 50))
    for chunk in chunks:
        for pk in chunk:
            _check_in_full(pk)
            sleep(0.1)
        rand = random.randint(3, 7)
        sleep(rand)


@app.task
def monitor_agents_task() -> None:
    q = Agent.objects.only("pk", "version", "last_seen", "overdue_time")
    agents: List[int] = [i.pk for i in q if i.has_nats and i.status != "online"]
    for agent in agents:
        _check_agent_service(agent)


def agent_update(pk: int) -> str:
    agent = Agent.objects.get(pk=pk)
    # skip if we can't determine the arch
    if agent.arch is None:
        logger.warning(f"Unable to determine arch on {agent.hostname}. Skipping.")
        return "noarch"

    # removed sqlite in 1.4.0 to get rid of cgo dependency
    # 1.3.0 has migration func to move from sqlite to win registry, so force an upgrade to 1.3.0 if old agent
    if pyver.parse(agent.version) >= pyver.parse("1.3.0"):
        version = settings.LATEST_AGENT_VER
        url = agent.winagent_dl
        inno = agent.win_inno_exe
    else:
        version = "1.3.0"
        inno = (
            "winagent-v1.3.0.exe" if agent.arch == "64" else "winagent-v1.3.0-x86.exe"
        )
        url = f"https://github.com/wh1te909/rmmagent/releases/download/v1.3.0/{inno}"

    if agent.has_nats:
        if pyver.parse(agent.version) <= pyver.parse("1.1.11"):
            if agent.pendingactions.filter(
                action_type="agentupdate", status="pending"
            ).exists():
                action = agent.pendingactions.filter(
                    action_type="agentupdate", status="pending"
                ).last()
                if pyver.parse(action.details["version"]) < pyver.parse(version):
                    action.delete()
                else:
                    return "pending"

            PendingAction.objects.create(
                agent=agent,
                action_type="agentupdate",
                details={
                    "url": url,
                    "version": version,
                    "inno": inno,
                },
            )
        else:
            nats_data = {
                "func": "agentupdate",
                "payload": {
                    "url": url,
                    "version": version,
                    "inno": inno,
                },
            }
            asyncio.run(agent.nats_cmd(nats_data, wait=False))

        return "created"
    else:
        logger.warning(
            f"{agent.hostname} v{agent.version} is running an unsupported version. Refusing to update."
        )

    return "not supported"


@app.task
def send_agent_update_task(pks: List[int], version: str) -> None:
    q = Agent.objects.filter(pk__in=pks)
    agents: List[int] = [
        i.pk for i in q if pyver.parse(i.version) < pyver.parse(version)
    ]
    chunks = (agents[i : i + 30] for i in range(0, len(agents), 30))
    for chunk in chunks:
        for pk in chunk:
            agent_update(pk)
            sleep(0.05)
        sleep(4)


@app.task
def auto_self_agent_update_task() -> None:
    core = CoreSettings.objects.first()
    if not core.agent_auto_update:
        return

    q = Agent.objects.only("pk", "version")
    pks: List[int] = [
        i.pk
        for i in q
        if pyver.parse(i.version) < pyver.parse(settings.LATEST_AGENT_VER)
    ]

    chunks = (pks[i : i + 30] for i in range(0, len(pks), 30))
    for chunk in chunks:
        for pk in chunk:
            agent_update(pk)
            sleep(0.05)
        sleep(4)


@app.task
def get_wmi_task():
    agents = Agent.objects.only("pk", "version", "last_seen", "overdue_time")
    online = [
        i
        for i in agents
        if pyver.parse(i.version) >= pyver.parse("1.2.0") and i.status == "online"
    ]
    chunks = (online[i : i + 50] for i in range(0, len(online), 50))
    for chunk in chunks:
        for agent in chunk:
            asyncio.run(agent.nats_cmd({"func": "wmi"}, wait=False))
            sleep(0.1)
        rand = random.randint(3, 7)
        sleep(rand)


@app.task
def sync_sysinfo_task():
    agents = Agent.objects.only("pk", "version", "last_seen", "overdue_time")
    online = [
        i
        for i in agents
        if pyver.parse(i.version) >= pyver.parse("1.1.3")
        and pyver.parse(i.version) <= pyver.parse("1.1.12")
        and i.status == "online"
    ]

    chunks = (online[i : i + 50] for i in range(0, len(online), 50))
    for chunk in chunks:
        for agent in chunk:
            asyncio.run(agent.nats_cmd({"func": "sync"}, wait=False))
            sleep(0.1)
        rand = random.randint(3, 7)
        sleep(rand)


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
    agents = Agent.objects.only(
        "pk", "last_seen", "overdue_time", "overdue_email_alert", "overdue_text_alert"
    )

    for agent in agents:
        if agent.overdue_email_alert or agent.overdue_text_alert:
            if agent.status == "overdue":
                outages = AgentOutage.objects.filter(agent=agent)
                if outages and outages.last().is_active:
                    continue

                outage = AgentOutage(agent=agent)
                outage.save()

                # add a null check history to allow gaps in graph
                for check in agent.agentchecks.all():
                    check.add_check_history(None)

                if agent.overdue_email_alert and not agent.maintenance_mode:
                    agent_outage_email_task.delay(pk=outage.pk)

                if agent.overdue_text_alert and not agent.maintenance_mode:
                    agent_outage_sms_task.delay(pk=outage.pk)


@app.task
def handle_agent_recovery_task(pk: int) -> None:
    sleep(10)
    from agents.models import RecoveryAction

    action = RecoveryAction.objects.get(pk=pk)
    if action.mode == "command":
        data = {"func": "recoverycmd", "recoverycommand": action.command}
    else:
        data = {"func": "recover", "payload": {"mode": action.mode}}

    asyncio.run(action.agent.nats_cmd(data, wait=False))


@app.task
def run_script_email_results_task(
    agentpk: int, scriptpk: int, nats_timeout: int, nats_data: dict, emails: List[str]
):
    agent = Agent.objects.get(pk=agentpk)
    script = Script.objects.get(pk=scriptpk)
    nats_data["func"] = "runscriptfull"
    r = asyncio.run(agent.nats_cmd(nats_data, timeout=nats_timeout))
    if r == "timeout":
        logger.error(f"{agent.hostname} timed out running script.")
        return

    CORE = CoreSettings.objects.first()
    subject = f"{agent.hostname} {script.name} Results"
    exec_time = "{:.4f}".format(r["execution_time"])
    body = (
        subject
        + f"\nReturn code: {r['retcode']}\nExecution time: {exec_time} seconds\nStdout: {r['stdout']}\nStderr: {r['stderr']}"
    )

    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = CORE.smtp_from_email

    if emails:
        msg["To"] = ", ".join(emails)
    else:
        msg["To"] = ", ".join(CORE.email_alert_recipients)

    msg.set_content(body)

    try:
        with smtplib.SMTP(CORE.smtp_host, CORE.smtp_port, timeout=20) as server:
            if CORE.smtp_requires_auth:
                server.ehlo()
                server.starttls()
                server.login(CORE.smtp_host_user, CORE.smtp_host_password)
                server.send_message(msg)
                server.quit()
            else:
                server.send_message(msg)
                server.quit()
    except Exception as e:
        logger.error(e)


@app.task
def remove_salt_task() -> None:
    if hasattr(settings, "KEEP_SALT") and settings.KEEP_SALT:
        return

    q = Agent.objects.only("pk", "version")
    agents = [i for i in q if pyver.parse(i.version) >= pyver.parse("1.3.0")]
    chunks = (agents[i : i + 50] for i in range(0, len(agents), 50))
    for chunk in chunks:
        for agent in chunk:
            asyncio.run(agent.nats_cmd({"func": "removesalt"}, wait=False))
            sleep(0.1)
        sleep(4)
