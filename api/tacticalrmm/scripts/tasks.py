import asyncio
from typing import List

from agents.models import Agent, AgentHistory
from scripts.models import Script
from tacticalrmm.celery import app
from tacticalrmm.constants import AgentHistoryType


@app.task
def handle_bulk_command_task(
    agentpks: list[int],
    cmd: str,
    shell: str,
    timeout,
    username,
    run_as_user: bool = False,
) -> None:
    nats_data = {
        "func": "rawcmd",
        "timeout": timeout,
        "payload": {
            "command": cmd,
            "shell": shell,
        },
        "run_as_user": run_as_user,
    }
    agent: "Agent"
    for agent in Agent.objects.filter(pk__in=agentpks):
        hist = AgentHistory.objects.create(
            agent=agent,
            type=AgentHistoryType.CMD_RUN,
            command=cmd,
            username=username,
        )
        nats_data["id"] = hist.pk

        asyncio.run(agent.nats_cmd(nats_data, wait=False))


@app.task
def handle_bulk_script_task(
    scriptpk: int,
    agentpks: List[int],
    args: List[str],
    timeout: int,
    username: str,
    run_as_user: bool = False,
) -> None:
    script = Script.objects.get(pk=scriptpk)
    agent: "Agent"
    for agent in Agent.objects.filter(pk__in=agentpks):
        hist = AgentHistory.objects.create(
            agent=agent,
            type=AgentHistoryType.SCRIPT_RUN,
            script=script,
            username=username,
        )
        agent.run_script(
            scriptpk=script.pk,
            args=args,
            timeout=timeout,
            history_pk=hist.pk,
            run_as_user=run_as_user,
        )
