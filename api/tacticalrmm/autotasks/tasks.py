import asyncio
import datetime as dt
import random
from time import sleep
from typing import Union, Optional

from autotasks.models import AutomatedTask
from agents.models import Agent
from django.utils import timezone as djangotime
from logs.models import DebugLog
from alerts.models import Alert
from autotasks.models import TaskResult
from tacticalrmm.celery import app


@app.task
def create_win_task_schedule(pk: int, agent_id: Optional[str] = None) -> str:
    task = AutomatedTask.objects.get(pk=pk)

    if agent_id:
        task.create_task_on_agent(Agent.objects.get(agent_id=agent_id))
    else:
        task.create_task_on_agent()

    return "ok"


@app.task
def modify_win_task(pk: int, agent_id: Optional[str] = None) -> str:
    task = AutomatedTask.objects.get(pk=pk)

    if agent_id:
        task.modify_task_on_agent(Agent.objects.get(agent_id=agent_id))
    else:
        task.modify_task_on_agent()

    return "ok"


@app.task
def delete_win_task_schedule(pk: int, agent_id: Optional[str] = None) -> str:
    task = AutomatedTask.objects.get(pk=pk)

    if agent_id:
        task.delete_task_on_agent(Agent.objects.get(agent_id=agent_id))
    else:
        task.delete_task_on_agent()

    return "ok"


@app.task
def run_win_task(pk: int, agent_id: Optional[str] = None) -> str:
    task = AutomatedTask.objects.get(pk=pk)

    if agent_id:
        task.run_win_task(Agent.objects.get(agent_id=agent_id))
    else:
        task.run_win_task()

    return "ok"


@app.task
def remove_orphaned_win_tasks(agentpk) -> None:
    from agents.models import Agent

    agent = Agent.objects.get(pk=agentpk)

    DebugLog.info(
        agent=agent,
        log_type="agent_issues",
        message=f"Orphaned task cleanup initiated on {agent.hostname}.",
    )

    r = asyncio.run(agent.nats_cmd({"func": "listschedtasks"}, timeout=10))

    if not isinstance(r, list) and not r:  # empty list
        DebugLog.error(
            agent=agent,
            log_type="agent_issues",
            message=f"Unable to clean up scheduled tasks on {agent.hostname}: {r}",
        )
        return

    agent_task_names = [task.win_task_name for task in agent.get_tasks_with_policies()]

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
                DebugLog.error(
                    agent=agent,
                    log_type="agent_issues",
                    message=f"Unable to clean up orphaned task {task} on {agent.hostname}: {ret}",
                )
            else:
                DebugLog.info(
                    agent=agent,
                    log_type="agent_issues",
                    message=f"Removed orphaned task {task} from {agent.hostname}",
                )

    DebugLog.info(
        agent=agent,
        log_type="agent_issues",
        message=f"Orphaned task cleanup finished on {agent.hostname}",
    )


@app.task
def handle_task_email_alert(pk: int, alert_interval: Union[float, None] = None) -> str:

    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    # first time sending email
    if not alert.email_sent:
        task_result = TaskResult.objects.get(
            task=alert.assigned_task, agent=alert.agent
        )
        sleep(random.randint(1, 10))
        task_result.send_email()
        alert.email_sent = djangotime.now()
        alert.save(update_fields=["email_sent"])
    else:
        if alert_interval:
            # send an email only if the last email sent is older than alert interval
            delta = djangotime.now() - dt.timedelta(days=alert_interval)
            if alert.email_sent < delta:
                task_result = TaskResult.objects.get(
                    task=alert.assigned_task, agent=alert.agent
                )
                sleep(random.randint(1, 10))
                task_result.send_email()
                alert.email_sent = djangotime.now()
                alert.save(update_fields=["email_sent"])

    return "ok"


@app.task
def handle_task_sms_alert(pk: int, alert_interval: Union[float, None] = None) -> str:

    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    # first time sending text
    if not alert.sms_sent:
        task_result = TaskResult.objects.get(
            task=alert.assigned_task, agent=alert.agent
        )
        sleep(random.randint(1, 3))
        task_result.send_sms()
        alert.sms_sent = djangotime.now()
        alert.save(update_fields=["sms_sent"])
    else:
        if alert_interval:
            # send a text only if the last text sent is older than alert interval
            delta = djangotime.now() - dt.timedelta(days=alert_interval)
            if alert.sms_sent < delta:
                task_result = TaskResult.objects.get(
                    task=alert.assigned_task, agent=alert.agent
                )
                sleep(random.randint(1, 3))
                task_result.send_sms()
                alert.sms_sent = djangotime.now()
                alert.save(update_fields=["sms_sent"])

    return "ok"


@app.task
def handle_resolved_task_sms_alert(pk: int) -> str:

    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    # first time sending text
    if not alert.resolved_sms_sent:
        task_result = TaskResult.objects.get(
            task=alert.assigned_task, agent=alert.agent
        )
        sleep(random.randint(1, 3))
        task_result.send_resolved_sms()
        alert.resolved_sms_sent = djangotime.now()
        alert.save(update_fields=["resolved_sms_sent"])

    return "ok"


@app.task
def handle_resolved_task_email_alert(pk: int) -> str:

    try:
        alert = Alert.objects.get(pk=pk)
    except Alert.DoesNotExist:
        return "alert not found"

    # first time sending email
    if not alert.resolved_email_sent:
        task_result = TaskResult.objects.get(
            task=alert.assigned_task, agent=alert.agent
        )
        sleep(random.randint(1, 10))
        task_result.send_resolved_email()
        alert.resolved_email_sent = djangotime.now()
        alert.save(update_fields=["resolved_email_sent"])

    return "ok"
