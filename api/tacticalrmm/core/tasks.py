import pytz
from loguru import logger

from django.conf import settings
from django.utils import timezone as djangotime
from tacticalrmm.celery import app
from accounts.models import User
from agents.models import Agent
from autotasks.models import AutomatedTask
from autotasks.tasks import delete_win_task_schedule

logger.configure(**settings.LOG_CONFIG)


@app.task
def core_maintenance_tasks():
    # cleanup any leftover agent user accounts
    agents = Agent.objects.values_list("agent_id", flat=True)
    users = User.objects.exclude(username__in=agents).filter(last_login=None)
    if users:
        users.delete()
        logger.info(
            "Removed leftover agent user accounts:", str([i.username for i in users])
        )

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
