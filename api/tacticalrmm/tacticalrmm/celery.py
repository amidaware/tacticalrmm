from __future__ import absolute_import, unicode_literals

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tacticalrmm.settings")

redis_host = f"redis://{settings.REDIS_HOST}"
app = Celery("tacticalrmm", backend=redis_host, broker=redis_host)
app.accept_content = ["application/json"]
app.result_serializer = "json"
app.task_serializer = "json"
app.conf.task_track_started = True
app.conf.worker_proc_alive_timeout = 30
app.conf.worker_max_tasks_per_child = 2
app.conf.broker_connection_retry_on_startup = True
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
    "remove-orphaned-tasks": {
        "task": "autotasks.tasks.remove_orphaned_win_tasks",
        "schedule": crontab(minute=50, hour="*/2"),
    },
    "agent-outages-task": {
        "task": "agents.tasks.agent_outages_task",
        "schedule": timedelta(seconds=150.0),
    },
    "unsnooze-alerts": {
        "task": "alerts.tasks.unsnooze_alerts",
        "schedule": crontab(minute=10, hour="*"),
    },
    "core-maintenance-tasks": {
        "task": "core.tasks.core_maintenance_tasks",
        "schedule": crontab(minute=15, hour="*"),
    },
    "cache-db-fields-task": {
        "task": "core.tasks.cache_db_fields_task",
        "schedule": crontab(minute="*/3", hour="*"),
    },
    "sync-scheduled-tasks": {
        "task": "core.tasks.sync_scheduled_tasks",
        "schedule": crontab(minute="*/2", hour="*"),
    },
    "sync-mesh-perms-task": {
        "task": "core.tasks.sync_mesh_perms_task",
        "schedule": crontab(minute="*/4", hour="*"),
    },
    "resolve-pending-actions": {
        "task": "core.tasks.resolve_pending_actions",
        "schedule": timedelta(seconds=100.0),
    },
    "resolve-alerts-task": {
        "task": "core.tasks.resolve_alerts_task",
        "schedule": timedelta(seconds=80.0),
    },
}


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))
