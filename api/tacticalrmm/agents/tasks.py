import asyncio
import datetime as dt
import random
from time import sleep
from typing import Union

from django.conf import settings
from django.utils import timezone as djangotime
from loguru import logger
from packaging import version as pyver

from agents.models import Agent
from core.models import CoreSettings
from logs.models import PendingAction
from scripts.models import Script
from tacticalrmm.celery import app
from tacticalrmm.utils import run_nats_api_cmd

logger.configure(**settings.LOG_CONFIG)


def agent_update(pk: int) -> str:
    agent = Agent.objects.get(pk=pk)

    if pyver.parse(agent.version) <= pyver.parse("1.1.11"):
        logger.warning(
            f"{agent.hostname} v{agent.version} is running an unsupported version. Refusing to auto update."
        )
        return "not supported"

    # skip if we can't determine the arch
    if agent.arch is None:
        logger.warning(
            f"Unable to determine arch on {agent.hostname}. Skipping agent update."
        )
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

    if agent.pendingactions.filter(
        action_type="agentupdate", status="pending"
    ).exists():
        agent.pendingactions.filter(
            action_type="agentupdate", status="pending"
        ).delete()

    PendingAction.objects.create(
        agent=agent,
        action_type="agentupdate",
        details={
            "url": url,
            "version": version,
            "inno": inno,
        },
    )

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


@app.task
def send_agent_update_task(pks: list[int]) -> None:
    chunks = (pks[i : i + 30] for i in range(0, len(pks), 30))
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
    pks: list[int] = [
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
def agent_outage_email_task(pk: int, alert_interval: Union[float, None] = None) -> str:
    from alerts.models import Alert

    alert = Alert.objects.get(pk=pk)

    if not alert.email_sent:
        sleep(random.randint(1, 15))
        alert.agent.send_outage_email()
        alert.email_sent = djangotime.now()
        alert.save(update_fields=["email_sent"])
    else:
        if alert_interval:
            # send an email only if the last email sent is older than alert interval
            delta = djangotime.now() - dt.timedelta(days=alert_interval)
            if alert.email_sent < delta:
                sleep(random.randint(1, 10))
                alert.agent.send_outage_email()
                alert.email_sent = djangotime.now()
                alert.save(update_fields=["email_sent"])

    return "ok"


@app.task
def agent_recovery_email_task(pk: int) -> str:
    from alerts.models import Alert

    sleep(random.randint(1, 15))
    alert = Alert.objects.get(pk=pk)
    alert.agent.send_recovery_email()
    alert.resolved_email_sent = djangotime.now()
    alert.save(update_fields=["resolved_email_sent"])

    return "ok"


@app.task
def agent_outage_sms_task(pk: int, alert_interval: Union[float, None] = None) -> str:
    from alerts.models import Alert

    alert = Alert.objects.get(pk=pk)

    if not alert.sms_sent:
        sleep(random.randint(1, 15))
        alert.agent.send_outage_sms()
        alert.sms_sent = djangotime.now()
        alert.save(update_fields=["sms_sent"])
    else:
        if alert_interval:
            # send an sms only if the last sms sent is older than alert interval
            delta = djangotime.now() - dt.timedelta(days=alert_interval)
            if alert.sms_sent < delta:
                sleep(random.randint(1, 10))
                alert.agent.send_outage_sms()
                alert.sms_sent = djangotime.now()
                alert.save(update_fields=["sms_sent"])

    return "ok"


@app.task
def agent_recovery_sms_task(pk: int) -> str:
    from alerts.models import Alert

    sleep(random.randint(1, 3))
    alert = Alert.objects.get(pk=pk)
    alert.agent.send_recovery_sms()
    alert.resolved_sms_sent = djangotime.now()
    alert.save(update_fields=["resolved_sms_sent"])

    return "ok"


@app.task
def agent_outages_task() -> None:
    from alerts.models import Alert

    agents = Agent.objects.only(
        "pk",
        "last_seen",
        "offline_time",
        "overdue_time",
        "overdue_email_alert",
        "overdue_text_alert",
        "overdue_dashboard_alert",
    )

    for agent in agents:
        if agent.status == "overdue":
            Alert.handle_alert_failure(agent)


@app.task
def run_script_email_results_task(
    agentpk: int,
    scriptpk: int,
    nats_timeout: int,
    emails: list[str],
    args: list[str] = [],
):
    agent = Agent.objects.get(pk=agentpk)
    script = Script.objects.get(pk=scriptpk)
    r = agent.run_script(
        scriptpk=script.pk, args=args, full=True, timeout=nats_timeout, wait=True
    )
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
def monitor_agents_task() -> None:
    agents = Agent.objects.only(
        "pk", "agent_id", "last_seen", "overdue_time", "offline_time"
    )
    ids = [i.agent_id for i in agents if i.status != "online"]
    run_nats_api_cmd("monitor", ids)


@app.task
def get_wmi_task() -> None:
    agents = Agent.objects.only(
        "pk", "agent_id", "last_seen", "overdue_time", "offline_time"
    )
    ids = [i.agent_id for i in agents if i.status == "online"]
    run_nats_api_cmd("wmi", ids)
