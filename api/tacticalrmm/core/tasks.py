import pytz
from django.utils import timezone as djangotime

from autotasks.models import AutomatedTask
from autotasks.tasks import delete_win_task_schedule
from checks.tasks import prune_check_history
from agents.tasks import clear_faults_task, prune_agent_history
from alerts.tasks import prune_resolved_alerts
from core.models import CoreSettings
from logs.tasks import prune_debug_log, prune_audit_log
from tacticalrmm.celery import app
from tacticalrmm.utils import AGENT_DEFER


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
    if core.check_history_prune_days > 0:  # type: ignore
        prune_check_history.delay(core.check_history_prune_days)  # type: ignore

    # remove old resolved alerts
    if core.resolved_alerts_prune_days > 0:  # type: ignore
        prune_resolved_alerts.delay(core.resolved_alerts_prune_days)  # type: ignore

    # remove old agent history
    if core.agent_history_prune_days > 0:  # type: ignore
        prune_agent_history.delay(core.agent_history_prune_days)  # type: ignore

    # remove old debug logs
    if core.debug_log_prune_days > 0:  # type: ignore
        prune_debug_log.delay(core.debug_log_prune_days)  # type: ignore

    # remove old audit logs
    if core.audit_log_prune_days > 0:  # type: ignore
        prune_audit_log.delay(core.audit_log_prune_days)  # type: ignore

    # clear faults
    if core.clear_faults_days > 0:  # type: ignore
        clear_faults_task.delay(core.clear_faults_days)  # type: ignore


@app.task
def cache_db_fields_task():
    from agents.models import Agent

    for agent in Agent.objects.defer(*AGENT_DEFER):
        agent.pending_actions_count = agent.pendingactions.filter(
            status="pending"
        ).count()
        agent.has_patches_pending = (
            agent.winupdates.filter(action="approve").filter(installed=False).exists()
        )
        agent.save(update_fields=["pending_actions_count", "has_patches_pending"])
