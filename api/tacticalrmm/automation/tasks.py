from loguru import logger
from tacticalrmm.celery import app
from django.conf import settings

from .models import AutomatedTask

logger.configure(**settings.LOG_CONFIG)

DAYS_OF_WEEK = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


@app.task
def create_win_task_schedule(pk):
    task = AutomatedTask.objects.get(pk=pk)

    if task.task_type == "scheduled":
        run_days = [DAYS_OF_WEEK.get(day) for day in task.run_time_days]

        resp = task.agent.salt_api_cmd(
            hostname=task.agent.salt_id,
            timeout=120,
            func="task.create_task",
            arg=[
                f"name={task.win_task_name}",
                "force=True",
                "action_type=Execute",
                'cmd="C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"',
                f'arguments="-m taskrunner -p {task.pk}"',
                "start_in=C:\\Program Files\\TacticalAgent",
                "trigger_type=Weekly",
                f'start_time="{task.run_time_minute}"',
                "ac_only=False",
                "stop_if_on_batteries=False",
            ],
            kwargs={"days_of_week": run_days},
        )

    elif task.task_type == "checkfailure" or task.task_type == "manual":
        resp = task.agent.salt_api_cmd(
            hostname=task.agent.salt_id,
            timeout=120,
            func="task.create_task",
            arg=[
                f"name={task.win_task_name}",
                "force=True",
                "action_type=Execute",
                'cmd="C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"',
                f'arguments="-m taskrunner -p {task.pk}"',
                "start_in=C:\\Program Files\\TacticalAgent",
                "trigger_type=Once",
                "ac_only=False",
                "stop_if_on_batteries=False",
            ],
        )

    msg = (
        f"{task.agent.hostname} task {task.name} was added with response: {resp.json()}"
    )
    logger.info(msg)

    return "ok"


@app.task
def delete_win_task_schedule(pk):
    task = AutomatedTask.objects.get(pk=pk)

    resp = task.agent.salt_api_cmd(
        hostname=task.agent.salt_id,
        timeout=120,
        func="task.delete_task",
        arg=[f"name={task.win_task_name}"],
    )

    task.delete()

    msg = f"{task.agent.hostname} task {task.name} was deleted with response: {resp.json()}"
    logger.info(msg)

    return "ok"


@app.task
def run_win_task(pk):
    task = AutomatedTask.objects.get(pk=pk)
    resp = task.agent.salt_api_cmd(
        hostname=task.agent.salt_id,
        timeout=120,
        func="task.run",
        arg=[f"name={task.win_task_name}"],
    )
    return "ok"
