import asyncio
import datetime as dt
from collections import namedtuple
from contextlib import suppress
from time import sleep
from typing import TYPE_CHECKING, Optional, Union

import msgpack
import nats
from django.utils import timezone as djangotime
from nats.errors import TimeoutError

from agents.models import Agent
from alerts.models import Alert
from autotasks.models import AutomatedTask, TaskResult
from tacticalrmm.celery import app
from tacticalrmm.constants import AGENT_STATUS_ONLINE, ORPHANED_WIN_TASK_LOCK
from tacticalrmm.helpers import rand_range, setup_nats_options
from tacticalrmm.utils import redis_lock

if TYPE_CHECKING:
    from nats.aio.client import Client as NATSClient


@app.task
def create_win_task_schedule(pk: int, agent_id: Optional[str] = None) -> str:
    with suppress(
        AutomatedTask.DoesNotExist,
        Agent.DoesNotExist,
    ):
        task = AutomatedTask.objects.get(pk=pk)

        if agent_id:
            task.create_task_on_agent(Agent.objects.get(agent_id=agent_id))
        else:
            task.create_task_on_agent()

    return "ok"


@app.task
def modify_win_task(pk: int, agent_id: Optional[str] = None) -> str:
    with suppress(
        AutomatedTask.DoesNotExist,
        Agent.DoesNotExist,
    ):
        task = AutomatedTask.objects.get(pk=pk)

        if agent_id:
            task.modify_task_on_agent(Agent.objects.get(agent_id=agent_id))
        else:
            task.modify_task_on_agent()

    return "ok"


@app.task
def delete_win_task_schedule(pk: int, agent_id: Optional[str] = None) -> str:
    with suppress(
        AutomatedTask.DoesNotExist,
        Agent.DoesNotExist,
    ):
        task = AutomatedTask.objects.get(pk=pk)

        if agent_id:
            task.delete_task_on_agent(Agent.objects.get(agent_id=agent_id))
        else:
            task.delete_task_on_agent()

    return "ok"


@app.task
def run_win_task(pk: int, agent_id: Optional[str] = None) -> str:
    with suppress(
        AutomatedTask.DoesNotExist,
        Agent.DoesNotExist,
    ):
        task = AutomatedTask.objects.get(pk=pk)

        if agent_id:
            task.run_win_task(Agent.objects.get(agent_id=agent_id))
        else:
            task.run_win_task()

    return "ok"


@app.task(bind=True)
def remove_orphaned_win_tasks(self) -> str:
    with redis_lock(ORPHANED_WIN_TASK_LOCK, self.app.oid) as acquired:
        if not acquired:
            return f"{self.app.oid} still running"

        from core.tasks import _get_agent_qs

        AgentTup = namedtuple("AgentTup", ["agent_id", "task_names"])
        items: "list[AgentTup]" = []
        exclude_tasks = ("TacticalRMM_SchedReboot",)

        for agent in _get_agent_qs():
            if agent.status == AGENT_STATUS_ONLINE:
                names = [task.win_task_name for task in agent.get_tasks_with_policies()]
                items.append(AgentTup._make([agent.agent_id, names]))

        async def _handle_task(nc: "NATSClient", sub, data, names) -> str:
            try:
                msg = await nc.request(
                    subject=sub, payload=msgpack.dumps(data), timeout=5
                )
            except TimeoutError:
                return "timeout"

            try:
                r = msgpack.loads(msg.data)
            except Exception as e:
                return str(e)

            if not isinstance(r, list):
                return "notlist"

            for name in r:
                if name.startswith(exclude_tasks):
                    # skip system tasks or any pending reboots
                    continue

                if name.startswith("TacticalRMM_") and name not in names:
                    nats_data = {
                        "func": "delschedtask",
                        "schedtaskpayload": {"name": name},
                    }
                    print(f"Deleting orphaned task: {name} on agent {sub}")
                    await nc.publish(subject=sub, payload=msgpack.dumps(nats_data))

            return "ok"

        async def _run() -> None:
            opts = setup_nats_options()
            try:
                nc = await nats.connect(**opts)
            except Exception as e:
                return str(e)

            payload = {"func": "listschedtasks"}
            tasks = [
                _handle_task(
                    nc=nc, sub=item.agent_id, data=payload, names=item.task_names
                )
                for item in items
            ]
            await asyncio.gather(*tasks)
            await nc.flush()
            await nc.close()

        asyncio.run(_run())
        return "completed"


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
        sleep(rand_range(100, 1500))
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
                sleep(rand_range(100, 1500))
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
        sleep(rand_range(100, 1500))
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
                sleep(rand_range(100, 1500))
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
        sleep(rand_range(100, 1500))
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
        sleep(rand_range(100, 1500))
        task_result.send_resolved_email()
        alert.resolved_email_sent = djangotime.now()
        alert.save(update_fields=["resolved_email_sent"])

    return "ok"
