import asyncio
import datetime as dt
import random
import tempfile
import json
import subprocess
import urllib.parse
from time import sleep
from typing import Union

from django.conf import settings
from django.utils import timezone as djangotime
from loguru import logger
from packaging import version as pyver

from agents.models import Agent
from core.models import CodeSignToken, CoreSettings
from logs.models import PendingAction
from scripts.models import Script
from tacticalrmm.celery import app
from tacticalrmm.utils import run_nats_api_cmd

logger.configure(**settings.LOG_CONFIG)


def agent_update(pk: int, codesigntoken: str = None, force: bool = False) -> str:
    from agents.utils import get_exegen_url

    agent = Agent.objects.get(pk=pk)

    if pyver.parse(agent.version) <= pyver.parse("1.3.0"):
        return "not supported"

    # skip if we can't determine the arch
    if agent.arch is None:
        logger.warning(
            f"Unable to determine arch on {agent.hostname}. Skipping agent update."
        )
        return "noarch"

    version = settings.LATEST_AGENT_VER
    inno = agent.win_inno_exe

    if codesigntoken is not None and pyver.parse(version) >= pyver.parse("1.5.0"):
        base_url = get_exegen_url() + "/api/v1/winagents/?"
        params = {"version": version, "arch": agent.arch, "token": codesigntoken}
        url = base_url + urllib.parse.urlencode(params)
    else:
        url = agent.winagent_dl

    if not force:
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
def force_code_sign(pks: list[int]) -> None:
    try:
        token = CodeSignToken.objects.first().token
    except:
        return

    chunks = (pks[i : i + 50] for i in range(0, len(pks), 50))
    for chunk in chunks:
        for pk in chunk:
            agent_update(pk=pk, codesigntoken=token, force=True)
            sleep(0.05)
        sleep(4)


@app.task
def send_agent_update_task(pks: list[int]) -> None:
    try:
        codesigntoken = CodeSignToken.objects.first().token
    except:
        codesigntoken = None

    chunks = (pks[i : i + 30] for i in range(0, len(pks), 30))
    for chunk in chunks:
        for pk in chunk:
            agent_update(pk, codesigntoken)
            sleep(0.05)
        sleep(4)


@app.task
def auto_self_agent_update_task() -> None:
    core = CoreSettings.objects.first()
    if not core.agent_auto_update:
        return

    try:
        codesigntoken = CodeSignToken.objects.first().token
    except:
        codesigntoken = None

    q = Agent.objects.only("pk", "version")
    pks: list[int] = [
        i.pk
        for i in q
        if pyver.parse(i.version) < pyver.parse(settings.LATEST_AGENT_VER)
    ]

    chunks = (pks[i : i + 30] for i in range(0, len(pks), 30))
    for chunk in chunks:
        for pk in chunk:
            agent_update(pk, codesigntoken)
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
        "agent_id",
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
def clear_faults_task(older_than_days: int) -> None:
    # https://github.com/wh1te909/tacticalrmm/issues/484
    agents = Agent.objects.exclude(last_seen__isnull=True).filter(
        last_seen__lt=djangotime.now() - djangotime.timedelta(days=older_than_days)
    )
    for agent in agents:
        if agent.agentchecks.exists():
            for check in agent.agentchecks.all():
                # reset check status
                check.status = "passing"
                check.save(update_fields=["status"])
                if check.alert.filter(resolved=False).exists():
                    check.alert.get(resolved=False).resolve()

        # reset overdue alerts
        agent.overdue_email_alert = False
        agent.overdue_text_alert = False
        agent.overdue_dashboard_alert = False
        agent.save(
            update_fields=[
                "overdue_email_alert",
                "overdue_text_alert",
                "overdue_dashboard_alert",
            ]
        )


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
    run_nats_api_cmd("wmi", ids, timeout=45)


@app.task
def agent_checkin_task() -> None:
    db = settings.DATABASES["default"]
    config = {
        "key": settings.SECRET_KEY,
        "natsurl": f"tls://{settings.ALLOWED_HOSTS[0]}:4222",
        "user": db["USER"],
        "pass": db["PASSWORD"],
        "host": db["HOST"],
        "port": int(db["PORT"]),
        "dbname": db["NAME"],
    }
    with tempfile.NamedTemporaryFile() as fp:
        with open(fp.name, "w") as f:
            json.dump(config, f)
        cmd = ["/usr/local/bin/nats-api", "-c", fp.name, "-m", "checkin"]
        subprocess.run(cmd, timeout=30)
