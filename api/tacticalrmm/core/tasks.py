import pytz
from django.conf import settings
from django.utils import timezone as djangotime
from loguru import logger

from autotasks.models import AutomatedTask
from autotasks.tasks import delete_win_task_schedule
from checks.tasks import prune_check_history
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

    # remove old CheckHistory data
    older_than = CoreSettings.objects.first().check_history_prune_days
    prune_check_history.delay(older_than)
