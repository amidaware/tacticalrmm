import smtplib
from email.message import EmailMessage

import pytz
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from loguru import logger
from twilio.rest import Client as TwClient

from logs.models import BaseAuditModel

logger.configure(**settings.LOG_CONFIG)

TZ_CHOICES = [(_, _) for _ in pytz.all_timezones]


class CoreSettings(BaseAuditModel):
    email_alert_recipients = ArrayField(
        models.EmailField(null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    sms_alert_recipients = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    twilio_number = models.CharField(max_length=255, null=True, blank=True)
    twilio_account_sid = models.CharField(max_length=255, null=True, blank=True)
    twilio_auth_token = models.CharField(max_length=255, null=True, blank=True)
    smtp_from_email = models.CharField(
        max_length=255, null=True, blank=True, default="from@example.com"
    )
    smtp_host = models.CharField(
        max_length=255, null=True, blank=True, default="smtp.gmail.com"
    )
    smtp_host_user = models.CharField(
        max_length=255, null=True, blank=True, default="admin@example.com"
    )
    smtp_host_password = models.CharField(
        max_length=255, null=True, blank=True, default="changeme"
    )
    smtp_port = models.PositiveIntegerField(default=587, null=True, blank=True)
    smtp_requires_auth = models.BooleanField(default=True)
    default_time_zone = models.CharField(
        max_length=255, choices=TZ_CHOICES, default="America/Los_Angeles"
    )
    # removes check history older than days
    check_history_prune_days = models.PositiveIntegerField(default=30)
    clear_faults_days = models.IntegerField(default=0)
    mesh_token = models.CharField(max_length=255, null=True, blank=True, default="")
    mesh_username = models.CharField(max_length=255, null=True, blank=True, default="")
    mesh_site = models.CharField(max_length=255, null=True, blank=True, default="")
    agent_auto_update = models.BooleanField(default=True)
    workstation_policy = models.ForeignKey(
        "automation.Policy",
        related_name="default_workstation_policy",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    server_policy = models.ForeignKey(
        "automation.Policy",
        related_name="default_server_policy",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    alert_template = models.ForeignKey(
        "alerts.AlertTemplate",
        related_name="default_alert_template",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        from alerts.tasks import cache_agents_alert_template
        from automation.tasks import generate_agent_checks_task

        if not self.pk and CoreSettings.objects.exists():
            raise ValidationError("There can only be one CoreSettings instance")

        # for install script
        if not self.pk:
            try:
                self.mesh_site = settings.MESH_SITE
                self.mesh_username = settings.MESH_USERNAME
                self.mesh_token = settings.MESH_TOKEN_KEY
            except:
                pass

        old_settings = type(self).objects.get(pk=self.pk) if self.pk else None
        super(BaseAuditModel, self).save(*args, **kwargs)

        # check if server polcies have changed and initiate task to reapply policies if so
        if (old_settings and old_settings.server_policy != self.server_policy) or (
            old_settings and old_settings.workstation_policy != self.workstation_policy
        ):
            generate_agent_checks_task.delay(all=True, create_tasks=True)

        if old_settings and old_settings.alert_template != self.alert_template:
            cache_agents_alert_template.delay()

    def __str__(self):
        return "Global Site Settings"

    @property
    def sms_is_configured(self):
        return all(
            [
                self.sms_alert_recipients,
                self.twilio_auth_token,
                self.twilio_account_sid,
                self.twilio_number,
            ]
        )

    @property
    def email_is_configured(self):
        # smtp with username/password authentication
        if (
            self.smtp_requires_auth
            and self.email_alert_recipients
            and self.smtp_from_email
            and self.smtp_host
            and self.smtp_host_user
            and self.smtp_host_password
            and self.smtp_port
        ):
            return True
        # smtp relay
        elif (
            not self.smtp_requires_auth
            and self.email_alert_recipients
            and self.smtp_from_email
            and self.smtp_host
            and self.smtp_port
        ):
            return True

        return False

    def send_mail(self, subject, body, alert_template=None, test=False):

        if not alert_template and not self.email_is_configured:
            if test:
                return "Missing required fields (need at least 1 recipient)"
            return False

        # override email from if alert_template is passed and is set
        if alert_template and alert_template.email_from:
            from_address = alert_template.email_from
        else:
            from_address = self.smtp_from_email

        # override email recipients if alert_template is passed and is set
        if alert_template and alert_template.email_recipients:
            email_recipients = ", ".join(alert_template.email_recipients)
        else:
            email_recipients = ", ".join(self.email_alert_recipients)

        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = from_address
            msg["To"] = email_recipients
            msg.set_content(body)

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=20) as server:
                if self.smtp_requires_auth:
                    server.ehlo()
                    server.starttls()
                    server.login(self.smtp_host_user, self.smtp_host_password)
                    server.send_message(msg)
                    server.quit()
                else:
                    # smtp relay. no auth required
                    server.send_message(msg)
                    server.quit()

        except Exception as e:
            logger.error(f"Sending email failed with error: {e}")
            if test:
                return str(e)
        else:
            return True

    def send_sms(self, body, alert_template=None):
        if not alert_template and not self.sms_is_configured:
            return

        # override email recipients if alert_template is passed and is set
        if alert_template and alert_template.text_recipients:
            text_recipients = alert_template.email_recipients
        else:
            text_recipients = self.sms_alert_recipients

        tw_client = TwClient(self.twilio_account_sid, self.twilio_auth_token)
        for num in text_recipients:
            try:
                tw_client.messages.create(body=body, to=num, from_=self.twilio_number)
            except Exception as e:
                logger.error(f"SMS failed to send: {e}")

    @staticmethod
    def serialize(core):
        # serializes the core and returns json
        from .serializers import CoreSerializer

        return CoreSerializer(core).data


FIELD_TYPE_CHOICES = (
    ("text", "Text"),
    ("number", "Number"),
    ("single", "Single"),
    ("multiple", "Multiple"),
    ("checkbox", "Checkbox"),
    ("datetime", "DateTime"),
)

MODEL_CHOICES = (("client", "Client"), ("site", "Site"), ("agent", "Agent"))


class CustomField(models.Model):

    order = models.PositiveIntegerField(default=0)
    model = models.CharField(max_length=25, choices=MODEL_CHOICES)
    type = models.CharField(max_length=25, choices=FIELD_TYPE_CHOICES, default="text")
    options = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    name = models.TextField(null=True, blank=True)
    required = models.BooleanField(blank=True, default=False)
    default_value_string = models.TextField(null=True, blank=True)
    default_value_bool = models.BooleanField(default=False)
    default_values_multiple = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    hide_in_ui = models.BooleanField(default=False)

    class Meta:
        unique_together = (("model", "name"),)

    def __str__(self):
        return self.name

    @property
    def default_value(self):
        if self.type == "multiple":
            return self.default_values_multiple
        elif self.type == "checkbox":
            return self.default_value_bool
        else:
            return self.default_value_string


class CodeSignToken(models.Model):
    token = models.CharField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and CodeSignToken.objects.exists():
            raise ValidationError("There can only be one CodeSignToken instance")

        super(CodeSignToken, self).save(*args, **kwargs)

    def __str__(self):
        return "Code signing token"


class GlobalKVStore(models.Model):
    name = models.CharField(max_length=25)
    value = models.TextField()

    def __str__(self):
        return self.name


class URLAction(models.Model):
    name = models.CharField(max_length=25)
    desc = models.CharField(max_length=100, null=True, blank=True)
    pattern = models.TextField()


RUN_ON_CHOICES = (
    ("client", "Client"),
    ("site", "Site"),
    ("agent", "Agent"),
    ("once", "Once"),
)

SCHEDULE_CHOICES = (("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"))


""" class GlobalTask(models.Model):
    script = models.ForeignKey(
        "scripts.Script",
        null=True,
        blank=True,
        related_name="script",
        on_delete=models.SET_NULL,
    )
    script_args = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    custom_field = models.OneToOneField(
        "core.CustomField",
        related_name="globaltask",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    timeout = models.PositiveIntegerField(default=120)
    retcode = models.IntegerField(null=True, blank=True)
    retvalue = models.TextField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, default="0.0000")
    run_schedule = models.CharField(
        max_length=25, choices=SCHEDULE_CHOICES, default="once"
    )
    run_on = models.CharField(
        max_length=25, choices=RUN_ON_CHOICES, default="once"
    ) """
