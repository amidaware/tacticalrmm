from tacticalrmm.celery import app


@app.task
def run_win_policy_autotasks_task(task: int) -> str:
    from autotasks.models import AutomatedTask

    try:
        policy_task = AutomatedTask.objects.get(pk=task)
    except AutomatedTask.DoesNotExist:
        return "AutomatedTask not found"

    if not policy_task.policy:
        return "AutomatedTask must be a policy"

    # get related agents from policy
    for agent in policy_task.policy.related_agents():
        policy_task.run_win_task(agent)

    return "ok"
