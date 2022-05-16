import asyncio
import datetime as dt
import random
from time import sleep
from typing import Optional, Union

from django.utils import timezone as djangotime

from agents.models import Agent
from alerts.models import Alert
from autotasks.models import AutomatedTask, TaskResult
from logs.models import DebugLog
from tacticalrmm.celery import app
from tacticalrmm.constants import DebugLogType


@app.task
def create_win_task_schedule(pk: int, agent_id: Optional[str] = None) -> str:
    try:
        task = AutomatedTask.objects.get(pk=pk)

        if agent_id:
            task.create_task_on_agent(Agent.objects.get(agent_id=agent_id))
        else:
            task.create_task_on_agent()
    except (AutomatedTask.DoesNotExist, Agent.DoesNotExist):
        pass

    return "ok"


@app.task
def modify_win_task(pk: int, agent_id: Optional[str] = None) -> str:
    try:
        task = AutomatedTask.objects.get(pk=pk)

        if agent_id:
            task.modify_task_on_agent(Agent.objects.get(agent_id=agent_id))
        else:
            task.modify_task_on_agent()
    except (AutomatedTask.DoesNotExist, Agent.DoesNotExist):
        pass

    return "ok"


@app.task
def delete_win_task_schedule(pk: int, agent_id: Optional[str] = None) -> str:
    try:
        task = AutomatedTask.objects.get(pk=pk)

        if agent_id:
            task.delete_task_on_agent(Agent.objects.get(agent_id=agent_id))
        else:
            task.delete_task_on_agent()
    except (AutomatedTask.DoesNotExist, Agent.DoesNotExist):
        pass

    return "ok"


@app.task
def run_win_task(pk: int, agent_id: Optional[str] = None) -> str:
    try:
        task = AutomatedTask.objects.get(pk=pk)

        if agent_id:
            task.run_win_task(Agent.objects.get(agent_id=agent_id))
        else:
            task.run_win_task()
    except (AutomatedTask.DoesNotExist, Agent.DoesNotExist):
        pass

    return "ok"


@app.task
def remove_orphaned_win_tasks() -> None:
    from agents.models import Agent

    for agent in Agent.online_agents():
        r = asyncio.run(agent.nats_cmd({"func": "listschedtasks"}, timeout=10))

        if not isinstance(r, list):  # empty list
            DebugLog.error(
                agent=agent,
                log_type=DebugLogType.AGENT_ISSUES,
                message=f"Unable to pull list of scheduled tasks on {agent.hostname}: {r}",
            )
            continue

        agent_task_names = [
            task.win_task_name for task in agent.get_tasks_with_policies()
        ]

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
                        log_type=DebugLogType.AGENT_ISSUES,
                        message=f"Unable to clean up orphaned task {task} on {agent.hostname}: {ret}",
                    )
                else:
                    DebugLog.info(
                        agent=agent,
                        log_type=DebugLogType.AGENT_ISSUES,
                        message=f"Removed orphaned task {task} from {agent.hostname}",
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
        sleep(random.randint(1, 5))
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
                sleep(random.randint(1, 5))
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
        sleep(random.randint(1, 5))
        task_result.send_resolved_email()
        alert.resolved_email_sent = djangotime.now()
        alert.save(update_fields=["resolved_email_sent"])

    return "ok"
