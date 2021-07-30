import asyncio

from packaging import version as pyver

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
        if pyver.parse(agent.version) >= pyver.parse("1.6.0"):
            hist = AgentHistory.objects.create(
                agent=agent,
                type="cmd_run",
                command=cmd,
                username=username,
            )
            nats_data["id"] = hist.pk

        asyncio.run(agent.nats_cmd(nats_data, wait=False))


@app.task
def handle_bulk_script_task(scriptpk, agentpks, args, timeout, username) -> None:
    script = Script.objects.get(pk=scriptpk)
    for agent in Agent.objects.filter(pk__in=agentpks):
        history_pk = 0
        if pyver.parse(agent.version) >= pyver.parse("1.6.0"):
            hist = AgentHistory.objects.create(
                agent=agent,
                type="script_run",
                script=script,
                username=username,
            )
            history_pk = hist.pk
        agent.run_script(
            scriptpk=script.pk, args=args, timeout=timeout, history_pk=history_pk
        )
