import datetime as dt
import pytz

from django.utils import timezone as djangotime
from django.dispatch import receiver
from django.db.models.signals import post_init

from .models import AutomatedTask
from .tasks import delete_win_task_schedule


@receiver(post_init, sender=AutomatedTask)
def handle_status(sender, instance: AutomatedTask, **kwargs):
    if instance.id is not None:
        # delete task if autoremove is set
        if instance.task_type == "runonce" and instance.remove_if_not_scheduled:

            agent_tz = pytz.timezone(instance.agent.timezone)
            task_time_utc = instance.run_time_date.replace(tzinfo=agent_tz).astimezone(
                pytz.utc
            )
            now = djangotime.now()

            if now > task_time_utc:
                delete_win_task_schedule.delay(instance.id)
