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
    "trmm-scheduler": {
        "task": "core.tasks.scheduled_task_runner",
        "schedule": crontab(),
    },
    "trmm-reports-scheduler": {
        "task": "ee.reporting.tasks.scheduled_reports_runner",
        "schedule": crontab(),
    },
    "dispatch-due-ai-tasks": {
        "task": "core.tasks.dispatch_due_ai_tasks",
        "schedule": crontab(),
    },
    "dispatch-due-bulk-ai-commands": {
        "task": "core.tasks.dispatch_due_bulk_ai_commands",
        "schedule": crontab(),
    },
    # AI ticket automation poller (no-op unless enabled in Global Settings)
    "poll-helpdesk-tickets": {
        "task": "core.tasks.poll_helpdesk_tickets",
        "schedule": timedelta(seconds=90.0),
    },
    "refresh-ai-model-catalog": {
        "task": "core.tasks.refresh_ai_model_catalog",
        "schedule": crontab(minute=17, hour="*/6"),
    },
    # ("ai-open-ticket-review" retired 2026-07-26: reports are operator-defined
    #  schedules now - see AIReportSchedule and dispatch_ai_report_schedules.)
    "ai-runtime-update-window": {
        "task": "core.tasks.run_ai_runtime_update",
        "schedule": timedelta(minutes=5),
    },
    # Each morning at 10:00, after the overnight scheduled jobs have run, decide whether
    # ticket-permission enforcement is safe to switch on and email the verdict with the
    # evidence. Reports only - it changes nothing by itself. Goes quiet once enforcing.
    "ai-caps-enforcement-readiness": {
        "task": "core.tasks.report_caps_enforcement_readiness",
        "schedule": crontab(minute=0, hour=10),
    },
    # An operation with no capability class is denied by product code. That is correct but
    # silent, so the system raises an internal notice ticket instead of relying on anyone
    # remembering to look. Hourly is plenty: the ticket is deduped per day.
    "ai-capability-health": {
        "task": "core.tasks.check_ai_capability_health",
        "schedule": crontab(minute=23),
    },
    # The other half of known-condition suppression: notice when a tracked condition stops
    # recurring and close its tracker with the evidence. Once a day is the right cadence -
    # the thresholds are in days.
    # Operator-defined reports (any cadence). Ticks often and each schedule decides whether it
    # is due, so cadences live in the database instead of in this file.
    "ai-dispatch-report-schedules": {
        "task": "core.tasks.dispatch_ai_report_schedules",
        "schedule": timedelta(minutes=5),
    },
    "ai-stand-down-resolved-conditions": {
        "task": "core.tasks.stand_down_resolved_conditions",
        "schedule": crontab(minute=17, hour=7),
    },
    "dispatch-due-ai-scheduled-actions": {
        "task": "core.tasks.dispatch_due_ai_scheduled_actions",
        "schedule": timedelta(seconds=60.0),
    },
    # AI Procedures miner. Runs often but SELF-GATES on the editable interval +
    # enabled flags in Global Settings, so the real cadence is set by the admin.
    "mine-ticket-procedures": {
        "task": "core.tasks.mine_ticket_procedures",
        "schedule": crontab(minute="*/30"),
    },
}


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))
