import pytz
from django.conf import settings
from django.utils import timezone as djangotime
from loguru import logger

from autotasks.models import AutomatedTask
from autotasks.tasks import delete_win_task_schedule
from checks.tasks import prune_check_history
from agents.tasks import clear_faults_task
from core.models import CoreSettings
from tacticalrmm.celery import app

logger.configure(**settings.LOG_CONFIG)


@app.task
def core_maintenance_tasks():
    # cleanup expired runonce tasks
    tasks = AutomatedTask.objects.filter(
        task_type="runonce",
        remove_if_not_scheduled=True,
    ).exclude(last_run=None)

    for task in tasks:
        agent_tz = pytz.timezone(task.agent.timezone)
        task_time_utc = task.run_time_date.replace(tzinfo=agent_tz).astimezone(pytz.utc)
        now = djangotime.now()

        if now > task_time_utc:
            delete_win_task_schedule.delay(task.pk)

    core = CoreSettings.objects.first()

    # remove old CheckHistory data
    if core.check_history_prune_days > 0:
        prune_check_history.delay(core.check_history_prune_days)
    # clear faults
    if core.clear_faults_days > 0:
        clear_faults_task.delay(core.clear_faults_days)


@app.task
def cache_db_fields_task():
    from agents.models import Agent

    for agent in Agent.objects.all():
        agent.pending_actions_count = agent.pendingactions.filter(
            status="pending"
        ).count()
        agent.has_patches_pending = (
            agent.winupdates.filter(action="approve").filter(installed=False).exists()
        )
        agent.save(update_fields=["pending_actions_count", "has_patches_pending"])
