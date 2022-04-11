import asyncio

from typing import List
from agents.models import Agent, AgentHistory
from scripts.models import Script

from tacticalrmm.celery import app


@app.task
def handle_bulk_command_task(
    agentpks, cmd, shell, timeout, username, run_on_offline=False
) -> None:
    nats_data = {
        "func": "rawcmd",
        "timeout": timeout,
        "payload": {
            "command": cmd,
            "shell": shell,
        },
    }
    for agent in Agent.objects.filter(pk__in=agentpks):
        hist = AgentHistory.objects.create(
            agent=agent,
            type="cmd_run",
            command=cmd,
            username=username,
        )
        nats_data["id"] = hist.pk

        asyncio.run(agent.nats_cmd(nats_data, wait=False))


@app.task
def handle_bulk_script_task(
    scriptpk: int, agentpks: List[int], args: List[str], timeout: int, username: str
) -> None:
    script = Script.objects.get(pk=scriptpk)
    for agent in Agent.objects.filter(pk__in=agentpks):
        hist = AgentHistory.objects.create(
            agent=agent,
            type="script_run",
            script=script,
            username=username,
        )
        agent.run_script(
            scriptpk=script.pk, args=args, timeout=timeout, history_pk=hist.pk
        )
