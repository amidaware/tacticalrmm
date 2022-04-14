import smtplib
from email.message import EmailMessage

from typing import Optional, Union, List, cast, TYPE_CHECKING
import pytz
import requests
from django.core.cache import cache
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from logs.models import LOG_LEVEL_CHOICES, BaseAuditModel, DebugLog
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client as TwClient

if TYPE_CHECKING:
    from alerts.models import AlertTemplate

TZ_CHOICES = [(_, _) for _ in pytz.all_timezones]

CORESETTINGS_CACHE_KEY = "core_settings"


class CoreSettings(BaseAuditModel):
    email_alert_recipients = ArrayField(
        models.EmailField(null=True, blank=True),
        blank=True,
        default=list,
    )
    sms_alert_recipients = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        blank=True,
        default=list,
    )
    twilio_number = models.CharField(max_length=255, null=True, blank=True)
    twilio_account_sid = models.CharField(max_length=255, null=True, blank=True)
    twilio_auth_token = models.CharField(max_length=255, null=True, blank=True)
    smtp_from_email = models.CharField(
        max_length=255, blank=True, default="from@example.com"
    )
    smtp_host = models.CharField(max_length=255, blank=True, default="smtp.gmail.com")
    smtp_host_user = models.CharField(
        max_length=255, blank=True, default="admin@example.com"
    )
    smtp_host_password = models.CharField(
        max_length=255, blank=True, default="changeme"
    )
    smtp_port = models.PositiveIntegerField(default=587, blank=True)
    smtp_requires_auth = models.BooleanField(default=True)
    default_time_zone = models.CharField(
        max_length=255, choices=TZ_CHOICES, default="America/Los_Angeles"
    )
    # removes check history older than days
    check_history_prune_days = models.PositiveIntegerField(default=30)
    resolved_alerts_prune_days = models.PositiveIntegerField(default=0)
    agent_history_prune_days = models.PositiveIntegerField(default=60)
    debug_log_prune_days = models.PositiveIntegerField(default=30)
    audit_log_prune_days = models.PositiveIntegerField(default=0)
    agent_debug_level = models.CharField(
        max_length=20, choices=LOG_LEVEL_CHOICES, default="info"
    )
    clear_faults_days = models.IntegerField(default=0)
    mesh_token = models.CharField(max_length=255, null=True, blank=True, default="")
    mesh_username = models.CharField(max_length=255, null=True, blank=True, default="")
    mesh_site = models.CharField(max_length=255, null=True, blank=True, default="")
    mesh_device_group = models.CharField(
        max_length=255, null=True, blank=True, default="TacticalRMM"
    )
    mesh_disable_auto_login = models.BooleanField(default=False)
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
    date_format = models.CharField(
        max_length=30, blank=True, default="MMM-DD-YYYY - HH:mm"
    )

    def save(self, *args, **kwargs) -> None:
        from alerts.tasks import cache_agents_alert_template

        cache.delete(CORESETTINGS_CACHE_KEY)

        if not self.pk and CoreSettings.objects.exists():
            raise ValidationError("There can only be one CoreSettings instance")

        # for install script
        if not self.pk:
            try:
                self.mesh_site = settings.MESH_SITE
                self.mesh_username = settings.MESH_USERNAME.lower()
                self.mesh_token = settings.MESH_TOKEN_KEY
            except:
                pass

        old_settings = type(self).objects.get(pk=self.pk) if self.pk else None
        super(BaseAuditModel, self).save(*args, **kwargs)

        if old_settings:
            if (
                old_settings.alert_template != self.alert_template
                or old_settings.server_policy != self.server_policy
                or old_settings.workstation_policy != self.workstation_policy
            ):
                cache_agents_alert_template.delay()

            if old_settings.workstation_policy != self.workstation_policy:
                cache.delete_many_pattern(f"site_workstation_*")

            if old_settings.server_policy != self.server_policy:
                cache.delete_many_pattern(f"site_server_*")

            if (
                old_settings.server_policy != self.server_policy
                or old_settings.workstation_policy != self.workstation_policy
            ):
                cache.delete_many_pattern("agent_*")

    def __str__(self) -> str:
        return "Global Site Settings"

    @property
    def sms_is_configured(self) -> bool:
        return all(
            [
                self.twilio_auth_token,
                self.twilio_account_sid,
                self.twilio_number,
            ]
        )

    @property
    def email_is_configured(self) -> bool:
        # smtp with username/password authentication
        if (
            self.smtp_requires_auth
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
            and self.smtp_from_email
            and self.smtp_host
            and self.smtp_port
        ):
            return True

        return False

    def send_mail(
        self,
        subject: str,
        body: str,
        alert_template: "Optional[AlertTemplate]" = None,
        test: bool = False,
    ) -> Union[bool, str]:
        if test and not self.email_is_configured:
            return "There needs to be at least one email recipient configured"
        # return since email must be configured to continue
        elif not self.email_is_configured:
            return "SMTP messaging not configured."

        # override email from if alert_template is passed and is set
        if alert_template and alert_template.email_from:
            from_address = alert_template.email_from
        else:
            from_address = self.smtp_from_email

        # override email recipients if alert_template is passed and is set
        if alert_template and alert_template.email_recipients:
            email_recipients = ", ".join(alert_template.email_recipients)
        elif self.email_alert_recipients:
            email_recipients = ", ".join(cast(List[str], self.email_alert_recipients))
        else:
            return "There needs to be at least one email recipient configured"

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
                    server.login(
                        self.smtp_host_user,
                        self.smtp_host_password,
                    )
                    server.send_message(msg)
                    server.quit()
                else:
                    # smtp relay. no auth required
                    server.send_message(msg)
                    server.quit()

        except Exception as e:
            DebugLog.error(message=f"Sending email failed with error: {e}")
            if test:
                return str(e)
        finally:
            return True

    def send_sms(
        self,
        body: str,
        alert_template: "Optional[AlertTemplate]" = None,
        test: bool = False,
    ) -> Union[str, bool]:
        if not self.sms_is_configured:
            return "Sms alerting is not setup correctly."

        # override email recipients if alert_template is passed and is set
        if alert_template and alert_template.text_recipients:
            text_recipients = alert_template.text_recipients
        elif self.sms_alert_recipients:
            text_recipients = cast(List[str], self.sms_alert_recipients)
        else:
            return "No sms recipients found"

        tw_client = TwClient(self.twilio_account_sid, self.twilio_auth_token)
        for num in text_recipients:
            try:
                tw_client.messages.create(body=body, to=num, from_=self.twilio_number)
            except TwilioRestException as e:
                DebugLog.error(message=f"SMS failed to send: {e}")
                if test:
                    return str(e)

        return True

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


class CustomField(BaseAuditModel):

    order = models.PositiveIntegerField(default=0)
    model = models.CharField(max_length=25, choices=MODEL_CHOICES)
    type = models.CharField(max_length=25, choices=FIELD_TYPE_CHOICES, default="text")
    options = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    name = models.CharField(max_length=30)
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

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def serialize(field):
        from .serializers import CustomFieldSerializer

        return CustomFieldSerializer(field).data

    @property
    def default_value(self):
        if self.type == "multiple":
            return self.default_values_multiple
        elif self.type == "checkbox":
            return self.default_value_bool
        else:
            return self.default_value_string

    def get_or_create_field_value(self, instance):
        from agents.models import Agent, AgentCustomField
        from clients.models import Client, ClientCustomField, Site, SiteCustomField

        if isinstance(instance, Agent):
            if AgentCustomField.objects.filter(field=self, agent=instance).exists():
                return AgentCustomField.objects.get(field=self, agent=instance)
            else:
                return AgentCustomField.objects.create(field=self, agent=instance)
        elif isinstance(instance, Client):
            if ClientCustomField.objects.filter(field=self, client=instance).exists():
                return ClientCustomField.objects.get(field=self, client=instance)
            else:
                return ClientCustomField.objects.create(field=self, client=instance)
        elif isinstance(instance, Site):
            if SiteCustomField.objects.filter(field=self, site=instance).exists():
                return SiteCustomField.objects.get(field=self, site=instance)
            else:
                return SiteCustomField.objects.create(field=self, site=instance)


class CodeSignToken(models.Model):
    token = models.CharField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and CodeSignToken.objects.exists():
            raise ValidationError("There can only be one CodeSignToken instance")

        super(CodeSignToken, self).save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        if not self.token:
            return False

        try:
            r = requests.post(
                f"{settings.EXE_GEN_URL}/api/v1/checktoken",
                json={"token": self.token},
                headers={"Content-type": "application/json"},
                timeout=15,
            )
        except:
            return False

        return r.status_code == 200

    def __str__(self):
        return "Code signing token"


class GlobalKVStore(BaseAuditModel):
    name = models.CharField(max_length=25)
    value = models.TextField()

    def __str__(self):
        return self.name

    @staticmethod
    def serialize(store):
        from .serializers import KeyStoreSerializer

        return KeyStoreSerializer(store).data


class URLAction(BaseAuditModel):
    name = models.CharField(max_length=25)
    desc = models.CharField(max_length=100, null=True, blank=True)
    pattern = models.TextField()

    def __str__(self):
        return self.name

    @staticmethod
    def serialize(action):
        from .serializers import URLActionSerializer

        return URLActionSerializer(action).data


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
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    execution_time = models.CharField(max_length=100, default="0.0000")
    run_schedule = models.CharField(
        max_length=25, choices=SCHEDULE_CHOICES, default="once"
    )
    run_on = models.CharField(
        max_length=25, choices=RUN_ON_CHOICES, default="once"
    ) """
