from loguru import logger
from tacticalrmm.celery import app
from django.conf import settings
import pytz
from django.utils import timezone as djangotime

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

    elif task.task_type == "runonce":

        # check if scheduled time is in the past
        agent_tz = pytz.timezone(task.agent.timezone)
        task_time_utc = task.run_time_date.replace(tzinfo=agent_tz).astimezone(pytz.utc)
        now = djangotime.now()
        if task_time_utc < now:
            task.run_time_date = now.astimezone(agent_tz).replace(
                tzinfo=pytz.utc
            ) + djangotime.timedelta(minutes=5)
            task.save()

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
                f'start_date="{task.run_time_date.strftime("%Y-%m-%d")}"',
                f'start_time="{task.run_time_date.strftime("%H:%M")}"',
                "ac_only=False",
                "stop_if_on_batteries=False",
                "start_when_available=True",
            ],
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
                'start_date="1975-01-01"',
                'start_time="01:00"',
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
    r = task.agent.salt_api_async(func="task.run", arg=[f"name={task.win_task_name}"])
    return "ok"


@app.task
def remove_orphaned_win_tasks(agentpk):
    from agents.models import Agent

    agent = Agent.objects.get(pk=agentpk)

    logger.info(f"Orphaned task cleanup initiated on {agent.hostname}.")

    r = agent.salt_api_cmd(
        timeout=15,
        func="task.list_tasks",
    )

    if r == "timeout" or r == "error":
        logger.error(
            f"Unable to clean up scheduled tasks on {agent.hostname}. Agent might be offline"
        )
        return "errtimeout"

    if not isinstance(r, list):
        logger.error(f"Unable to clean up scheduled tasks on {agent.hostname}: {r}")
        return "notlist"

    agent_task_names = list(agent.autotasks.values_list("win_task_name", flat=True))

    exclude_tasks = (
        "TacticalRMM_fixmesh",
        "TacticalRMM_SchedReboot",
        "TacticalRMM_saltwatchdog",  # will be implemented in future
    )

    for task in r:
        if task.startswith(exclude_tasks):
            # skip system tasks or any pending reboots
            continue

        if task.startswith("TacticalRMM_") and task not in agent_task_names:
            # delete task since it doesn't exist in UI
            ret = agent.salt_api_cmd(
                timeout=20,
                func="task.delete_task",
                arg=[f"name={task}"],
            )
            if isinstance(ret, bool) and ret is True:
                logger.info(f"Removed orphaned task {task} from {agent.hostname}")
            else:
                logger.error(
                    f"Unable to clean up orphaned task {task} on {agent.hostname}: {ret}"
                )

    logger.info(f"Orphaned task cleanup finished on {agent.hostname}")
