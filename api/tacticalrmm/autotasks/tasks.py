from loguru import logger
from tacticalrmm.celery import app
from django.conf import settings

from .models import AutomatedTask
from logs.models import PendingAction

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
def create_win_task_schedule(pk, pending_action=False):
    task = AutomatedTask.objects.get(pk=pk)

    if task.task_type == "scheduled":
        run_days = [DAYS_OF_WEEK.get(day) for day in task.run_time_days]

        r = task.agent.salt_api_cmd(
            timeout=20,
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
        r = task.agent.salt_api_cmd(
            timeout=20,
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

    if r == "timeout" or r == "error" or (isinstance(r, bool) and not r):
        # don't create pending action if this task was initiated by a pending action
        if not pending_action:
            PendingAction(
                agent=task.agent,
                action_type="taskaction",
                details={"action": "taskcreate", "task_id": task.id},
            ).save()
            task.sync_status = "notsynced"
            task.save(update_fields=["sync_status"])

        logger.error(
            f"Unable to create scheduled task {task.win_task_name} on {task.agent.hostname}. It will be created when the agent checks in."
        )
        return

    # clear pending action since it was successful
    if pending_action:
        pendingaction = PendingAction.objects.get(pk=pending_action)
        pendingaction.status = "completed"
        pendingaction.save(update_fields=["status"])

    task.sync_status = "synced"
    task.save(update_fields=["sync_status"])

    logger.info(f"{task.agent.hostname} task {task.name} was successfully created")

    return "ok"


@app.task
def enable_or_disable_win_task(pk, action, pending_action=False):
    task = AutomatedTask.objects.get(pk=pk)

    r = task.agent.salt_api_cmd(
        timeout=20,
        func="task.edit_task",
        arg=[f"name={task.win_task_name}", f"enabled={action}"],
    )

    if r == "timeout" or r == "error" or (isinstance(r, bool) and not r):
        # don't create pending action if this task was initiated by a pending action
        if not pending_action:
            PendingAction(
                agent=task.agent,
                action_type="taskaction",
                details={
                    "action": "tasktoggle",
                    "value": action,
                    "task_id": task.id,
                },
            ).save()
            task.sync_status = "notsynced"
            task.save(update_fields=["sync_status"])

        logger.error(
            f"Unable to update the scheduled task {task.win_task_name} on {task.agent.hostname}. It will be updated when the agent checks in."
        )
        return

    # clear pending action since it was successful
    if pending_action:
        pendingaction = PendingAction.objects.get(pk=pending_action)
        pendingaction.status = "completed"
        pendingaction.save(update_fields=["status"])

    task.sync_status = "synced"
    task.save(update_fields=["sync_status"])
    logger.info(f"{task.agent.hostname} task {task.name} was edited.")
    return "ok"


@app.task
def delete_win_task_schedule(pk, pending_action=False):
    task = AutomatedTask.objects.get(pk=pk)

    r = task.agent.salt_api_cmd(
        timeout=20,
        func="task.delete_task",
        arg=[f"name={task.win_task_name}"],
    )

    if r == "timeout" or r == "error" or (isinstance(r, bool) and not r):
        # don't create pending action if this task was initiated by a pending action
        if not pending_action:
            PendingAction(
                agent=task.agent,
                action_type="taskaction",
                details={"action": "taskdelete", "task_id": task.id},
            ).save()
            task.sync_status = "pendingdeletion"
            task.save(update_fields=["sync_status"])

        logger.error(
            f"Unable to delete scheduled task {task.win_task_name} on {task.agent.hostname}. It was marked pending deletion and will be removed when the agent checks in."
        )
        return

    # complete pending action since it was successful
    if pending_action:
        pendingaction = PendingAction.objects.get(pk=pending_action)
        pendingaction.status = "completed"
        pendingaction.save(update_fields=["status"])

    task.delete()
    logger.info(f"{task.agent.hostname} task {task.name} was deleted.")
    return "ok"


@app.task
def run_win_task(pk):
    task = AutomatedTask.objects.get(pk=pk)
    task.agent.salt_api_async(func="task.run", arg=[f"name={task.win_task_name}"])
    return "ok"
