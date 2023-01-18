import asyncio
from typing import TYPE_CHECKING, List

import msgpack
import nats

from agents.models import Agent, AgentHistory
from scripts.models import Script
from tacticalrmm.celery import app
from tacticalrmm.constants import AgentHistoryType
from tacticalrmm.helpers import setup_nats_options

if TYPE_CHECKING:
    from nats.aio.client import Client as NATSClient


@app.task
def handle_bulk_command_task(
    agentpks: list[int],
    cmd: str,
    shell: str,
    timeout,
    username,
    run_as_user: bool = False,
) -> None:

    items = []
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
        tmp = {**nats_data}
        tmp["id"] = hist.pk
        items.append((agent.agent_id, tmp))

    async def _run_cmd(nc: "NATSClient", sub, data) -> None:
        await nc.publish(subject=sub, payload=msgpack.dumps(data))

    async def _run() -> None:
        opts = setup_nats_options()
        try:
            nc = await nats.connect(**opts)
        except Exception as e:
            print(e)
            return

        tasks = [_run_cmd(nc=nc, sub=item[0], data=item[1]) for item in items]
        await asyncio.gather(*tasks)
        await nc.close()

    asyncio.run(_run())


@app.task
def handle_bulk_script_task(
    scriptpk: int,
    agentpks: List[int],
    args: List[str],
    timeout: int,
    username: str,
    run_as_user: bool = False,
    env_vars: list[str] = [],
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
            env_vars=env_vars,
        )
