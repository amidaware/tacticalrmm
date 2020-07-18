from automation.models import Policy
from checks.models import Check
from agents.models import Agent

import autotasks

from tacticalrmm.celery import app


@app.task
def generate_agent_checks_from_policies_task(
    policypk, many=False, clear=False, parent_checks=[]
):

    if many:
        policy_list = Policy.objects.filter(pk__in=policypk)
        for policy in policy_list:
            for agent in policy.related_agents():
                agent.generate_checks_from_policies(
                    clear=clear, parent_checks=parent_checks
                )
    else:
        policy = Policy.objects.get(pk=policypk)
        for agent in policy.related_agents():
            agent.generate_checks_from_policies(
                clear=clear, parent_checks=parent_checks
            )


@app.task
def generate_agent_checks_by_location_task(location, clear=False, parent_checks=[]):

    policy = Policy.objects.get(pk=policypk)
    for agent in Agent.objects.filter(**location):
        agent.generate_checks_from_policies(clear=clear, parent_checks=parent_checks)


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
        disk=check.disk,
        ip=check.ip,
        script=check.script,
        pass_if_start_pending=check.pass_if_start_pending,
        restart_if_stopped=check.restart_if_stopped,
        log_name=check.log_name,
        event_id=check.event_id,
        event_type=check.event_type,
        fail_when=check.fail_when,
        search_last_days=check.search_last_days,
        email_alert=check.email_alert,
        text_alert=check.text_alert,
    )


@app.task
def generate_agent_tasks_from_policies_task(
    policypk, many=False, clear=False, parent_tasks=[]
):

    if many:
        policy_list = Policy.objects.filter(pk__in=policypk)
        for policy in policy_list:
            for agent in policy.related_agents():
                agent.generate_tasks_from_policies(
                    clear=clear, parent_tasks=parent_tasks
                )
    else:
        policy = Policy.objects.get(pk=policypk)
        for agent in policy.related_agents():
            agent.generate_tasks_from_policies(clear=clear, parent_tasks=parent_tasks)


@app.task
def generate_agent_tasks_by_location_task(location, clear=False, parent_tasks=[]):

    policy = Policy.objects.get(pk=policypk)
    for agent in Agent.objects.filter(**location):
        agent.generate_tasks_from_policies(clear=clear, parent_tasks=parent_tasks)


@app.task
def delete_policy_autotask_task(taskpk):

    for task in autotasks.models.AutomatedTask.objects.filter(parent_task=taskpk):
        autotasks.tasks.delete_win_task_schedule.delay(task.pk)


@app.task
def run_win_policy_autotask_task(task_pks):

    for task in task_pks:
        autotasks.tasks.run_win_task.delay(task)


@app.task
def update_policy_task_fields_task(taskpk):

    task = autotasks.models.AutomatedTask.objects.get(pk=taskpk)

    tasks = autotasks.models.AutomatedTask.objects.filter(parent_task=taskpk).update(
        enabled=task.enabled
    )

    for autotask in tasks:
        autotasks.tasks.enable_or_disable_win_task(autotask.pk, task.enabled)
