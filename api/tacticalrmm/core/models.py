from django.db import models
from django.core.exceptions import ValidationError


class CoreSettings(models.Model):
    disk_check_interval = models.PositiveIntegerField(default=300)
    cpuload_check_interval = models.PositiveIntegerField(default=300)
    mem_check_interval = models.PositiveIntegerField(default=300)
    win_svc_check_interval = models.PositiveIntegerField(default=300)

    def save(self, *args, **kwargs):
        if not self.pk and CoreSettings.objects.exists():
            raise ValidationError("There can only be one CoreSettings instance")

        return super(CoreSettings, self).save(*args, **kwargs)

    def __str__(self):
        return "Global Site Settings"
