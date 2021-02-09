from automation.models import Policy
from autotasks.models import AutomatedTask
from checks.models import Check
from agents.models import Agent

from tacticalrmm.celery import app


@app.task
def generate_agent_checks_from_policies_task(policypk, create_tasks=False):

    policy = Policy.objects.get(pk=policypk)

    if policy.is_default_server_policy and policy.is_default_workstation_policy:
        agents = Agent.objects.prefetch_related("policy").only("pk", "monitoring_type")
    elif policy.is_default_server_policy:
        agents = Agent.objects.filter(monitoring_type="server").only(
            "pk", "monitoring_type"
        )
    elif policy.is_default_workstation_policy:
        agents = Agent.objects.filter(monitoring_type="workstation").only(
            "pk", "monitoring_type"
        )
    else:
        agents = policy.related_agents().only("pk")

    for agent in agents:
        agent.generate_checks_from_policies()
        if create_tasks:
            agent.generate_tasks_from_policies()


@app.task
def generate_agent_checks_task(agentpks, create_tasks=False):
    for agent in Agent.objects.filter(pk__in=agentpks):
        agent.generate_checks_from_policies()

        if create_tasks:
            agent.generate_tasks_from_policies()


@app.task
def generate_agent_checks_by_location_task(location, mon_type, create_tasks=False):

    for agent in Agent.objects.filter(**location).filter(monitoring_type=mon_type):
        agent.generate_checks_from_policies()

        if create_tasks:
            agent.generate_tasks_from_policies()


@app.task
def generate_all_agent_checks_task(mon_type, create_tasks=False):
    for agent in Agent.objects.filter(monitoring_type=mon_type):
        agent.generate_checks_from_policies()

        if create_tasks:
            agent.generate_tasks_from_policies()


@app.task
def delete_policy_check_task(checkpk):

    Check.objects.filter(parent_check=checkpk).delete()


@app.task
def update_policy_check_fields_task(checkpk):

    check = Check.objects.get(pk=checkpk)

    Check.objects.filter(parent_check=checkpk).update(
        warning_threshold=check.warning_threshold,
        error_threshold=check.error_threshold,
        alert_severity=check.alert_severity,
        name=check.name,
        disk=check.disk,
        fails_b4_alert=check.fails_b4_alert,
        ip=check.ip,
        script=check.script,
        script_args=check.script_args,
        info_return_codes=check.info_return_codes,
        warning_return_codes=check.warning_return_codes,
        timeout=check.timeout,
        pass_if_start_pending=check.pass_if_start_pending,
        pass_if_svc_not_exist=check.pass_if_svc_not_exist,
        restart_if_stopped=check.restart_if_stopped,
        log_name=check.log_name,
        event_id=check.event_id,
        event_id_is_wildcard=check.event_id_is_wildcard,
        event_type=check.event_type,
        event_source=check.event_source,
        event_message=check.event_message,
        fail_when=check.fail_when,
        search_last_days=check.search_last_days,
        email_alert=check.email_alert,
        text_alert=check.text_alert,
        dashboard_alert=check.dashboard_alert,
    )


@app.task
def generate_agent_tasks_from_policies_task(policypk):

    policy = Policy.objects.get(pk=policypk)

    if policy.is_default_server_policy and policy.is_default_workstation_policy:
        agents = Agent.objects.prefetch_related("policy").only("pk", "monitoring_type")
    elif policy.is_default_server_policy:
        agents = Agent.objects.filter(monitoring_type="server").only(
            "pk", "monitoring_type"
        )
    elif policy.is_default_workstation_policy:
        agents = Agent.objects.filter(monitoring_type="workstation").only(
            "pk", "monitoring_type"
        )
    else:
        agents = policy.related_agents()

    for agent in agents:
        agent.generate_tasks_from_policies()


@app.task
def generate_agent_tasks_by_location_task(location, mon_type):

    for agent in Agent.objects.filter(**location).filter(monitoring_type=mon_type):
        agent.generate_tasks_from_policies()


@app.task
def delete_policy_autotask_task(taskpk):
    from autotasks.tasks import delete_win_task_schedule
    from autotasks.models import AutomatedTask

    for task in AutomatedTask.objects.filter(parent_task=taskpk):
        delete_win_task_schedule.delay(task.pk)


@app.task
def run_win_policy_autotask_task(task_pks):
    from autotasks.tasks import run_win_task

    for task in task_pks:
        run_win_task.delay(task)


@app.task
def update_policy_task_fields_task(taskpk, update_agent=False):
    from autotasks.tasks import enable_or_disable_win_task

    task = AutomatedTask.objects.get(pk=taskpk)

    AutomatedTask.objects.filter(parent_task=taskpk).update(
        alert_severity=task.alert_severity,
        email_alert=task.email_alert,
        text_alert=task.text_alert,
        dashboard_alert=task.dashboard_alert,
        script=task.script,
        script_args=task.script_args,
        name=task.name,
        timeout=task.timeout,
        enabled=task.enabled,
    )

    if update_agent:
        for task in AutomatedTask.objects.filter(parent_task=taskpk):
            enable_or_disable_win_task.delay(task.pk, task.enabled)
