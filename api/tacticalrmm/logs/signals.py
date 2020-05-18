import datetime as dt

from django.dispatch import receiver
from django.db.models.signals import post_init

from .models import PendingAction


@receiver(post_init, sender=PendingAction)
def handle_status(sender, instance: PendingAction, **kwargs):
    if instance.id is not None:
        # change status to completed once scheduled reboot date/time has expired
        if instance.action_type == "schedreboot" and instance.status == "pending":

            reboot_time = dt.datetime.strptime(
                instance.details["time"], "%Y-%m-%d %H:%M:%S"
            )
            now = dt.datetime.now()

            if now > reboot_time:
                instance.status = "completed"
                instance.save(update_fields=["status"])
