import datetime as dt

import pytz
from django.db.models.signals import post_init
from django.dispatch import receiver
from django.utils import timezone as djangotime

from .models import PendingAction


@receiver(post_init, sender=PendingAction)
def handle_status(sender, instance: PendingAction, **kwargs):
    if instance.pk:
        # change status to completed once scheduled reboot date/time has expired
        if instance.action_type == "schedreboot" and instance.status == "pending":

            reboot_time = dt.datetime.strptime(
                instance.details["time"], "%Y-%m-%d %H:%M:%S"
            )

            # need to convert agent tz to UTC in order to compare
            agent_tz = pytz.timezone(instance.agent.timezone)
            localized = agent_tz.localize(reboot_time)

            now = djangotime.now()
            reboot_time_utc = localized.astimezone(pytz.utc)

            if now > reboot_time_utc:
                instance.status = "completed"
                instance.save(update_fields=["status"])
