import asyncio

from tacticalrmm.celery import app
from agents.models import Agent
from scripts.models import Script


@app.task
def handle_bulk_command_task(agentpks, cmd, shell, timeout):
    agents = Agent.objects.filter(pk__in=agentpks)

    agents_nats = [agent for agent in agents if agent.has_nats]
    agents_salt = [agent for agent in agents if not agent.has_nats]
    minions = [agent.salt_id for agent in agents_salt]

    if minions:
        Agent.salt_batch_async(
            minions=minions,
            func="cmd.run_bg",
            kwargs={
                "cmd": cmd,
                "shell": shell,
                "timeout": timeout,
            },
        )

    if agents_nats:
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
def handle_bulk_script_task(scriptpk, agentpks, args, timeout):
    script = Script.objects.get(pk=scriptpk)
    agents = Agent.objects.filter(pk__in=agentpks)

    agents_nats = [agent for agent in agents if agent.has_nats]
    agents_salt = [agent for agent in agents if not agent.has_nats]
    minions = [agent.salt_id for agent in agents_salt]

    if minions:
        Agent.salt_batch_async(
            minions=minions,
            func="win_agent.run_script",
            kwargs={
                "filepath": script.filepath,
                "filename": script.filename,
                "shell": script.shell,
                "timeout": timeout,
                "args": args,
                "bg": True if script.shell == "python" else False,  # salt bg script bug
            },
        )

    if agents_nats:
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
