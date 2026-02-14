import logging
from typing import Set

from django.db import models

from autotasks.models import AutomatedTask, TaskResult
from tacticalrmm.constants import TaskSyncStatus

logger = logging.getLogger(__name__)


class OpenframeScriptSchedule(models.Model):
    managed_task = models.OneToOneField(
        "autotasks.AutomatedTask",
        on_delete=models.CASCADE,
        related_name="openframe_script_schedule",
        help_text="The AutomatedTask that holds all schedule config and script actions.",
    )

    assigned_agents = models.ManyToManyField(
        "agents.Agent",
        related_name="openframe_script_schedules",
        blank=True,
        help_text="Agents this schedule is deployed to.",
    )

    class Meta:
        verbose_name = "Openframe Script Schedule"
        verbose_name_plural = "Openframe Script Schedules"

    def __str__(self) -> str:
        task_name = self.managed_task.name if self.managed_task_id else "no-task"
        return f"OpenframeScriptSchedule(pk={self.pk}, task='{task_name}')"

    # ------------------------------------------------------------------
    # TaskResult lifecycle
    # ------------------------------------------------------------------

    def sync_task_results(self) -> dict:
        """
        Ensure a TaskResult row exists for every assigned agent,
        and remove stale rows for agents no longer assigned.

        Returns {"created": int, "deleted": int}.
        """
        if not self.managed_task_id:
            return {"created": 0, "deleted": 0}

        task = self.managed_task

        current_agent_ids: Set[int] = set(
            self.assigned_agents.values_list("pk", flat=True)
        )
        existing_agent_ids: Set[int] = set(
            TaskResult.objects.filter(task=task).values_list("agent_id", flat=True)
        )

        # Create missing
        to_create = current_agent_ids - existing_agent_ids
        created = 0
        if to_create:
            objs = TaskResult.objects.bulk_create(
                [
                    TaskResult(
                        agent_id=aid,
                        task=task,
                        sync_status=TaskSyncStatus.SYNCED,
                    )
                    for aid in to_create
                ],
                ignore_conflicts=True,
            )
            created = len(objs)

        # Remove stale
        to_remove = existing_agent_ids - current_agent_ids
        deleted = 0
        if to_remove:
            deleted, _ = TaskResult.objects.filter(
                task=task, agent_id__in=to_remove
            ).delete()

        logger.info(
            f"OpenframeScriptSchedule pk={self.pk}: "
            f"synced TaskResults created={created} deleted={deleted}"
        )
        return {"created": created, "deleted": deleted}

    # ------------------------------------------------------------------
    # Cascade delete
    # ------------------------------------------------------------------

    def delete(self, *args, **kwargs):
        """
        Delete the managed AutomatedTask first (cascades to all TaskResult rows),
        then delete self.
        """
        task = self.managed_task
        super().delete(*args, **kwargs)
        if task:
            task.delete()
