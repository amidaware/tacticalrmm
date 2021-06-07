from typing import Any, Dict, List, Union

from tacticalrmm.celery import app


@app.task(retry_backoff=5, retry_jitter=True, retry_kwargs={"max_retries": 5})
def generate_agent_checks_task(
    policy: int = None,
    site: int = None,
    client: int = None,
    agents: List[int] = list(),
    all: bool = False,
    create_tasks: bool = False,
) -> Union[str, None]:
    from agents.models import Agent
    from automation.models import Policy

    p = Policy.objects.get(pk=policy) if policy else None

    # generate checks on all agents if all is specified or if policy is default server/workstation policy
    if (p and p.is_default_server_policy and p.is_default_workstation_policy) or all:
        a = Agent.objects.prefetch_related("policy").only("pk", "monitoring_type")

    # generate checks on all servers if policy is a default servers policy
    elif p and p.is_default_server_policy:
        a = Agent.objects.filter(monitoring_type="server").only("pk", "monitoring_type")

    # generate checks on all workstations if policy is a default workstations policy
    elif p and p.is_default_workstation_policy:
        a = Agent.objects.filter(monitoring_type="workstation").only(
            "pk", "monitoring_type"
        )

    # generate checks on a list of supplied agents
    elif agents:
        a = Agent.objects.filter(pk__in=agents)

    # generate checks on agents affected by supplied policy
    elif policy:
        a = p.related_agents().only("pk")

    # generate checks that has specified site
    elif site:
        a = Agent.objects.filter(site_id=site)

    # generate checks that has specified client
    elif client:
        a = Agent.objects.filter(site__client_id=client)
    else:
        a = []

    for agent in a:
        agent.generate_checks_from_policies()
        if create_tasks:
            agent.generate_tasks_from_policies()

    return "ok"


@app.task(
    acks_late=True, retry_backoff=5, retry_jitter=True, retry_kwargs={"max_retries": 5}
)
# updates policy managed check fields on agents
def update_policy_check_fields_task(check: int) -> str:
    from checks.models import Check

    c: Check = Check.objects.get(pk=check)
    update_fields: Dict[Any, Any] = {}

    for field in c.policy_fields_to_copy:
        update_fields[field] = getattr(c, field)

    Check.objects.filter(parent_check=check).update(**update_fields)

    return "ok"


@app.task(retry_backoff=5, retry_jitter=True, retry_kwargs={"max_retries": 5})
# generates policy tasks on agents affected by a policy
def generate_agent_autotasks_task(policy: int = None) -> str:
    from agents.models import Agent
    from automation.models import Policy

    p: Policy = Policy.objects.get(pk=policy)

    if p and p.is_default_server_policy and p.is_default_workstation_policy:
        agents = Agent.objects.prefetch_related("policy").only("pk", "monitoring_type")
    elif p and p.is_default_server_policy:
        agents = Agent.objects.filter(monitoring_type="server").only(
            "pk", "monitoring_type"
        )
    elif p and p.is_default_workstation_policy:
        agents = Agent.objects.filter(monitoring_type="workstation").only(
            "pk", "monitoring_type"
        )
    else:
        agents = p.related_agents().only("pk")

    for agent in agents:
        agent.generate_tasks_from_policies()

    return "ok"


@app.task(
    acks_late=True,
    retry_backoff=5,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def delete_policy_autotasks_task(task: int) -> str:
    from autotasks.models import AutomatedTask

    for t in AutomatedTask.objects.filter(parent_task=task):
        t.delete_task_on_agent()

    return "ok"


@app.task
def run_win_policy_autotasks_task(task: int) -> str:
    from autotasks.models import AutomatedTask

    for t in AutomatedTask.objects.filter(parent_task=task):
        t.run_win_task()

    return "ok"


@app.task(
    acks_late=True,
    retry_backoff=5,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def update_policy_autotasks_fields_task(task: int, update_agent: bool = False) -> str:
    from autotasks.models import AutomatedTask

    t = AutomatedTask.objects.get(pk=task)
    update_fields: Dict[str, Any] = {}

    for field in t.policy_fields_to_copy:
        update_fields[field] = getattr(t, field)

    AutomatedTask.objects.filter(parent_task=task).update(**update_fields)

    if update_agent:
        for t in AutomatedTask.objects.filter(parent_task=task).exclude(
            sync_status="initial"
        ):
            t.modify_task_on_agent()

    return "ok"
