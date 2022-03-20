from tacticalrmm.celery import app

@app.task
def run_win_policy_autotasks_task(task: int) -> str:
    from autotasks.models import AutomatedTask

    for t in AutomatedTask.objects.filter(parent_task=task):
        t.run_win_task()

    return "ok"
