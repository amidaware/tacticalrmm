from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tacticalrmm.settings")

app = Celery(
    "tacticalrmm",
    backend="redis://" + settings.REDIS_HOST,
    broker="redis://" + settings.REDIS_HOST,
)
# app.config_from_object('django.conf:settings', namespace='CELERY')
app.broker_url = "redis://" + settings.REDIS_HOST + ":6379"  # type: ignore
app.result_backend = "redis://" + settings.REDIS_HOST + ":6379"  # type: ignore
app.accept_content = ["application/json"]  # type: ignore
app.result_serializer = "json"  # type: ignore
app.task_serializer = "json"  # type: ignore
app.conf.task_track_started = True
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "auto-approve-win-updates": {
        "task": "winupdate.tasks.auto_approve_updates_task",
        "schedule": crontab(minute=2, hour="*/8"),
    },
    "install-scheduled-win-updates": {
        "task": "winupdate.tasks.check_agent_update_schedule_task",
        "schedule": crontab(minute=5, hour="*"),
    },
    "agent-auto-update": {
        "task": "agents.tasks.auto_self_agent_update_task",
        "schedule": crontab(minute=35, hour="*"),
    },
    "monitor-agents": {
        "task": "agents.tasks.monitor_agents_task",
        "schedule": crontab(minute="*/7"),
    },
    "get-wmi": {
        "task": "agents.tasks.get_wmi_task",
        "schedule": crontab(minute=18, hour="*/5"),
    },
}


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):

    from agents.tasks import agent_outages_task, agent_checkin_task
    from alerts.tasks import unsnooze_alerts
    from core.tasks import core_maintenance_tasks, cache_db_fields_task

    sender.add_periodic_task(45.0, agent_checkin_task.s())
    sender.add_periodic_task(60.0, agent_outages_task.s())
    sender.add_periodic_task(60.0 * 30, core_maintenance_tasks.s())
    sender.add_periodic_task(60.0 * 60, unsnooze_alerts.s())
    sender.add_periodic_task(90.0, cache_db_fields_task.s())
