import asyncio
import datetime as dt
import random
from time import sleep
from typing import Union

from django.conf import settings
from django.utils import timezone as djangotime
from loguru import logger

from autotasks.models import AutomatedTask
from tacticalrmm.celery import app

logger.configure(**settings.LOG_CONFIG)


@app.task
def create_win_task_schedule(pk):
    task = AutomatedTask.objects.get(pk=pk)

    task.create_task_on_agent()

    return "ok"


@app.task
def enable_or_disable_win_task(pk):
    task = AutomatedTask.objects.get(pk=pk)

    task.modify_task_on_agent()

    return "ok"


@app.task
def delete_win_task_schedule(pk):
    task = AutomatedTask.objects.get(pk=pk)

    task.delete_task_on_agent()
    return "ok"


@app.task
def run_win_task(pk):
    task = AutomatedTask.objects.get(pk=pk)
    task.run_win_task()
    return "ok"


@app.task
def remove_orphaned_win_tasks(agentpk):
    from agents.models import Agent

    agent = Agent.objects.get(pk=agentpk)

    logger.info(f"Orphaned task cleanup initiated on {agent.hostname}.")

    r = asyncio.run(agent.nats_cmd({"func": "listschedtasks"}, timeout=10))

    if not isinstance(r, list) and not r:  # empty list
        logger.error(f"Unable to clean up scheduled tasks on {agent.hostname}: {r}")
        return "notlist"

    agent_task_names = list(agent.autotasks.values_list("win_task_name", flat=True))

    exclude_tasks = (
        "TacticalRMM_fixmesh",
        "TacticalRMM_SchedReboot",
        "TacticalRMM_sync",
        "TacticalRMM_agentupdate",
    )

    for task in r:
        if task.startswith(exclude_tasks):
            # skip system tasks or any pending reboots
            continue

        if task.startswith("TacticalRMM_") and task not in agent_task_names:
            # delete task since it doesn't exist in UI
            nats_data = {
                "func": "delschedtask",
                "schedtaskpayload": {"name": task},
            }
            ret = asyncio.run(agent.nats_cmd(nats_data, timeout=10))
            if ret != "ok":
                logger.error(
                    f"Unable to clean up orphaned task {task} on {agent.hostname}: {ret}"
                )
            else:
                logger.info(f"Removed orphaned task {task} from {agent.hostname}")

    logger.info(f"Orphaned task cleanup finished on {agent.hostname}")


@app.task
def handle_task_email_alert(pk: int, alert_interval: Union[float, None] = None) -> str:
    from alerts.models import Alert

    alert = Alert.objects.get(pk=pk)

    # first time sending email
    if not alert.email_sent:
        sleep(random.randint(1, 10))
        alert.assigned_task.send_email()
        alert.email_sent = djangotime.now()
        alert.save(update_fields=["email_sent"])
    else:
        if alert_interval:
            # send an email only if the last email sent is older than alert interval
            delta = djangotime.now() - dt.timedelta(days=alert_interval)
            if alert.email_sent < delta:
                sleep(random.randint(1, 10))
                alert.assigned_task.send_email()
                alert.email_sent = djangotime.now()
                alert.save(update_fields=["email_sent"])

    return "ok"


@app.task
def handle_task_sms_alert(pk: int, alert_interval: Union[float, None] = None) -> str:
    from alerts.models import Alert

    alert = Alert.objects.get(pk=pk)

    # first time sending text
    if not alert.sms_sent:
        sleep(random.randint(1, 3))
        alert.assigned_task.send_sms()
        alert.sms_sent = djangotime.now()
        alert.save(update_fields=["sms_sent"])
    else:
        if alert_interval:
            # send a text only if the last text sent is older than alert interval
            delta = djangotime.now() - dt.timedelta(days=alert_interval)
            if alert.sms_sent < delta:
                sleep(random.randint(1, 3))
                alert.assigned_task.send_sms()
                alert.sms_sent = djangotime.now()
                alert.save(update_fields=["sms_sent"])

    return "ok"


@app.task
def handle_resolved_task_sms_alert(pk: int) -> str:
    from alerts.models import Alert

    alert = Alert.objects.get(pk=pk)

    # first time sending text
    if not alert.resolved_sms_sent:
        sleep(random.randint(1, 3))
        alert.assigned_task.send_resolved_sms()
        alert.resolved_sms_sent = djangotime.now()
        alert.save(update_fields=["resolved_sms_sent"])

    return "ok"


@app.task
def handle_resolved_task_email_alert(pk: int) -> str:
    from alerts.models import Alert

    alert = Alert.objects.get(pk=pk)

    # first time sending email
    if not alert.resolved_email_sent:
        sleep(random.randint(1, 10))
        alert.assigned_task.send_resolved_email()
        alert.resolved_email_sent = djangotime.now()
        alert.save(update_fields=["resolved_email_sent"])

    return "ok"
