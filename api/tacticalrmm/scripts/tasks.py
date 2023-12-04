import asyncio

from django.conf import settings

from agents.models import Agent, AgentHistory
from scripts.models import Script
from tacticalrmm.celery import app
from tacticalrmm.constants import AgentHistoryType
from tacticalrmm.nats_utils import abulk_nats_command


@app.task
def bulk_command_task(
    *,
    agent_pks: list[int],
    cmd: str,
    shell: str,
    timeout: int,
    username: str,
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
    for agent in Agent.objects.filter(pk__in=agent_pks):
        hist = AgentHistory.objects.create(
            agent=agent,
            type=AgentHistoryType.CMD_RUN,
            command=cmd,
            username=username,
        )
        tmp = {**nats_data}
        tmp["id"] = hist.pk
        items.append((agent.agent_id, tmp))

    asyncio.run(abulk_nats_command(items=items))


@app.task
def bulk_script_task(
    *,
    script_pk: int,
    agent_pks: list[int],
    args: list[str] = [],
    timeout: int,
    username: str,
    run_as_user: bool = False,
    env_vars: list[str] = [],
) -> None:
    script = Script.objects.get(pk=script_pk)
    # always override if set on script model
    if script.run_as_user:
        run_as_user = True

    items = []
    agent: "Agent"
    for agent in Agent.objects.filter(pk__in=agent_pks):
        hist = AgentHistory.objects.create(
            agent=agent,
            type=AgentHistoryType.SCRIPT_RUN,
            script=script,
            username=username,
        )
        data = {
            "func": "runscriptfull",
            "id": hist.pk,
            "timeout": timeout,
            "script_args": script.parse_script_args(agent, script.shell, args),
            "payload": {
                "code": script.code,
                "shell": script.shell,
            },
            "run_as_user": run_as_user,
            "env_vars": script.parse_script_env_vars(agent, script.shell, env_vars),
            "nushell_enable_config": settings.NUSHELL_ENABLE_CONFIG,
            "deno_default_permissions": settings.DENO_DEFAULT_PERMISSIONS,
        }
        tup = (agent.agent_id, data)
        items.append(tup)

    asyncio.run(abulk_nats_command(items=items))
