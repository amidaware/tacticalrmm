import asyncio

from agents.models import Agent
from scripts.models import Script
from tacticalrmm.celery import app


@app.task
def handle_bulk_command_task(agentpks, cmd, shell, timeout) -> None:
    agents = Agent.objects.filter(pk__in=agentpks)
    agents_nats = [agent for agent in agents if agent.has_nats]
    nats_data = {
        "func": "rawcmd",
        "timeout": timeout,
        "payload": {
            "command": cmd,
            "shell": shell,
        },
    }
    for agent in agents_nats:
        asyncio.run(agent.nats_cmd(nats_data, wait=False))


@app.task
def handle_bulk_script_task(scriptpk, agentpks, args, timeout) -> None:
    script = Script.objects.get(pk=scriptpk)
    agents = Agent.objects.filter(pk__in=agentpks)
    agents_nats = [agent for agent in agents if agent.has_nats]
    nats_data = {
        "func": "runscript",
        "timeout": timeout,
        "script_args": args,
        "payload": {
            "code": script.code,
            "shell": script.shell,
        },
    }
    for agent in agents_nats:
        asyncio.run(agent.nats_cmd(nats_data, wait=False))
