import datetime as dt

from django.db.models.signals import post_init
from django.dispatch import receiver

from tacticalrmm.constants import PAAction, PAStatus
from tacticalrmm.helpers import date_is_in_past

from .models import PendingAction


@receiver(post_init, sender=PendingAction)
def handle_status(sender, instance: PendingAction, **kwargs):
    if instance.pk:
        # change status to completed once scheduled reboot date/time has expired
        if (
            instance.action_type == PAAction.SCHED_REBOOT
            and instance.status == PAStatus.PENDING
        ):
            reboot_time = dt.datetime.strptime(
                instance.details["time"], "%Y-%m-%d %H:%M:%S"
            )
            if date_is_in_past(
                datetime_obj=reboot_time, agent_tz=instance.agent.timezone
            ):
                instance.status = PAStatus.COMPLETED
                instance.save(update_fields=["status"])
