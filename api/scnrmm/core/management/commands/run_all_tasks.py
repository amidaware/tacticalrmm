from django.core.management.base import BaseCommand

from agents.tasks import agent_outages_task, auto_self_agent_update_task
from alerts.tasks import unsnooze_alerts
from autotasks.tasks import remove_orphaned_win_tasks
from core.tasks import (
    cache_db_fields_task,
    core_maintenance_tasks,
    resolve_alerts_task,
    resolve_pending_actions,
    sync_mesh_perms_task,
    sync_scheduled_tasks,
)
from winupdate.tasks import auto_approve_updates_task, check_agent_update_schedule_task


class Command(BaseCommand):
    help = "Run all celery tasks"

    def handle(self, *args, **kwargs):
        auto_self_agent_update_task.delay()
        agent_outages_task.delay()
        unsnooze_alerts.delay()
        cache_db_fields_task.delay()
        core_maintenance_tasks.delay()
        resolve_pending_actions.delay()
        resolve_alerts_task.delay()
        sync_scheduled_tasks.delay()
        remove_orphaned_win_tasks.delay()
        auto_approve_updates_task.delay()
        check_agent_update_schedule_task.delay()
        sync_mesh_perms_task.delay()
