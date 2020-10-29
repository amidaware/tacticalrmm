from automation.models import Policy
from checks.models import Check
from agents.models import Agent

from tacticalrmm.celery import app


@app.task
def generate_agent_checks_from_policies_task(
    ###
    # copies the policy checks to all affected agents
    #
    # clear: clears all policy checks first
    # create_tasks: also create tasks after checks are generated
    ###
    policypk,
    clear=False,
    create_tasks=False,
):

    policy = Policy.objects.get(pk=policypk)
    for agent in policy.related_agents():
        agent.generate_checks_from_policies(clear=clear)
        if create_tasks:
            agent.generate_tasks_from_policies(
                clear=clear,
            )


@app.task
def generate_agent_checks_by_location_task(
    location, mon_type, clear=False, create_tasks=False
):

    for agent in Agent.objects.filter(**location).filter(monitoring_type=mon_type):
        agent.generate_checks_from_policies(clear=clear)

        if create_tasks:
            agent.generate_tasks_from_policies(clear=clear)


@app.task
def generate_all_agent_checks_task(mon_type, clear=False, create_tasks=False):
    for agent in Agent.objects.filter(monitoring_type=mon_type):
        agent.generate_checks_from_policies(clear=clear)

        if create_tasks:
            agent.generate_tasks_from_policies(clear=clear)


@app.task
def delete_policy_check_task(checkpk):

    Check.objects.filter(parent_check=checkpk).delete()


@app.task
def update_policy_check_fields_task(checkpk):

    check = Check.objects.get(pk=checkpk)

    Check.objects.filter(parent_check=checkpk).update(
        threshold=check.threshold,
        name=check.name,
        fails_b4_alert=check.fails_b4_alert,
        ip=check.ip,
        script_args=check.script_args,
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
    )


@app.task
def generate_agent_tasks_from_policies_task(policypk, clear=False):

    policy = Policy.objects.get(pk=policypk)
    for agent in policy.related_agents():
        agent.generate_tasks_from_policies(clear=clear)


@app.task
def generate_agent_tasks_by_location_task(location, mon_type, clear=False):

    for agent in Agent.objects.filter(**location).filter(monitoring_type=mon_type):
        agent.generate_tasks_from_policies(clear=clear)


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
def update_policy_task_fields_task(taskpk, enabled):
    from autotasks.models import AutomatedTask
    from autotasks.tasks import enable_or_disable_win_task

    tasks = AutomatedTask.objects.filter(parent_task=taskpk)

    tasks.update(enabled=enabled)

    for autotask in tasks:
        enable_or_disable_win_task(autotask.pk, enabled)
