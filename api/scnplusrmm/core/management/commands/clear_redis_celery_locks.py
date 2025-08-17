from django.core.cache import cache
from django.core.management.base import BaseCommand

from tacticalrmm.constants import (
    AGENT_OUTAGES_LOCK,
    ORPHANED_WIN_TASK_LOCK,
    RESOLVE_ALERTS_LOCK,
    SYNC_MESH_PERMS_TASK_LOCK,
    SYNC_SCHED_TASK_LOCK,
)


class Command(BaseCommand):
    help = "Clear redis celery locks. Should only be ran while celery/beat is stopped."

    def handle(self, *args, **kwargs):
        for key in (
            AGENT_OUTAGES_LOCK,
            ORPHANED_WIN_TASK_LOCK,
            RESOLVE_ALERTS_LOCK,
            SYNC_SCHED_TASK_LOCK,
            SYNC_MESH_PERMS_TASK_LOCK,
        ):
            cache.delete(key)
