from loguru import logger
import pytz

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings

logger.configure(**settings.LOG_CONFIG)

TZ_CHOICES = [(_, _) for _ in pytz.all_timezones]


class CoreSettings(models.Model):
    email_alert_recipients = ArrayField(
        models.EmailField(null=True, blank=True), null=True, blank=True, default=list,
    )
    smtp_use_tls = models.BooleanField(default=True)
    smtp_host = models.CharField(
        max_length=255, null=True, blank=True, default="smtp.gmail.com"
    )
    smtp_host_user = models.EmailField(
        null=True, blank=True, default="admin@example.com"
    )
    smtp_host_password = models.CharField(
        max_length=255, null=True, blank=True, default="changeme"
    )
    smtp_port = models.PositiveIntegerField(default=587, null=True, blank=True)
    default_time_zone = models.CharField(
        max_length=255, choices=TZ_CHOICES, default="America/Los_Angeles"
    )

    def save(self, *args, **kwargs):
        if not self.pk and CoreSettings.objects.exists():
            raise ValidationError("There can only be one CoreSettings instance")

        return super(CoreSettings, self).save(*args, **kwargs)

    def __str__(self):
        return "Global Site Settings"

    @property
    def email_is_configured(self):
        if (
            self.email_alert_recipients
            and self.smtp_host
            and self.smtp_host_user
            and self.smtp_host_password
            and self.smtp_port
        ):
            return True
        else:
            return False

    def send_mail(self, subject, body):

        if not self.email_is_configured:
            return False

        try:
            backend = EmailBackend(
                host=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_host_user,
                password=self.smtp_host_password,
                use_tls=self.smtp_use_tls,
                fail_silently=False,
            )

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=self.smtp_host_user,
                to=self.email_alert_recipients,
                connection=backend,
            )

            email.send()
        except Exception as e:
            logger.error(f"Sending email failed with error: {e}")
