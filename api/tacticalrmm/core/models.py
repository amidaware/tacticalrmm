import smtplib
import traceback
from contextlib import suppress
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import formatdate
from typing import TYPE_CHECKING, List, Optional, cast

import requests
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client as TwClient

from logs.models import BaseAuditModel, DebugLog
from tacticalrmm.constants import (
    ALL_TIMEZONES,
    CORESETTINGS_CACHE_KEY,
    CustomFieldModel,
    CustomFieldType,
    DarwinTerminalShellChoices,
    DebugLogLevel,
    LinuxTerminalShellChoices,
    MonthlyType,
    ScheduleType,
    TerminalModeChoices,
    URLActionRestMethod,
    URLActionType,
    WindowsTerminalShellChoices,
)
from tacticalrmm.logger import logger

if TYPE_CHECKING:
    from alerts.models import AlertTemplate

TZ_CHOICES = [(_, _) for _ in ALL_TIMEZONES]


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
    smtp_from_name = models.CharField(max_length=255, null=True, blank=True)
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
    report_history_prune_days = models.PositiveIntegerField(default=0)
    agent_debug_level = models.CharField(
        max_length=20, choices=DebugLogLevel.choices, default=DebugLogLevel.INFO
    )
    clear_faults_days = models.IntegerField(default=0)
    mesh_token = models.CharField(max_length=255, null=True, blank=True, default="")
    mesh_username = models.CharField(max_length=255, null=True, blank=True, default="")
    mesh_site = models.CharField(max_length=255, null=True, blank=True, default="")
    mesh_device_group = models.CharField(
        max_length=255, null=True, blank=True, default="TacticalRMM"
    )
    mesh_company_name = models.CharField(max_length=255, null=True, blank=True)
    sync_mesh_with_trmm = models.BooleanField(default=True)
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
    open_ai_token = models.CharField(max_length=255, null=True, blank=True)
    open_ai_model = models.CharField(
        max_length=255, blank=True, default="gpt-3.5-turbo"
    )
    # Pi.dev AI assistant module
    ai_module_enabled = models.BooleanField(default=False)
    ai_persist_history = models.BooleanField(default=True)
    ai_require_approval = models.BooleanField(default=True)
    # Admin-authored policy text injected into every AI session's system prompt
    # (chat + scheduled runs). Documents WHEN to open helpdesk tickets AND HOW
    # (the ticketing API calls themselves) - fully dynamic, no code changes to
    # switch ticketing systems.
    ai_helpdesk_prompt = models.TextField(blank=True, default="")
    # Generic ticketing API access for the helpdesk_api_request tool. The AI
    # writes {{HELPDESK_API_KEY}} in request bodies; the bridge substitutes the
    # real key server-side (the key is never placed in the AI's context).
    ai_helpdesk_api_base_url = models.CharField(max_length=255, blank=True, default="")
    ai_helpdesk_api_key = models.CharField(max_length=255, blank=True, default="")
    # Admin-authored JS integration ("helpdesk.js") defining deterministic
    # operations (create_ticket, reply, note, submit_report, ...) for ANY
    # ticketing system. Runs on the bridge; the AI calls the operations by name.
    # This is the "precise code" companion to the natural-language policy above.
    ai_helpdesk_code = models.TextField(blank=True, default="")
    enable_server_scripts = models.BooleanField(default=True)
    enable_server_webterminal = models.BooleanField(default=False)
    notify_on_info_alerts = models.BooleanField(default=False)
    notify_on_warning_alerts = models.BooleanField(default=True)

    block_local_user_logon = models.BooleanField(default=False)
    sso_enabled = models.BooleanField(default=False)

    default_shell_windows = models.CharField(
        max_length=32,
        choices=WindowsTerminalShellChoices.choices,
        default=WindowsTerminalShellChoices.CMD,
    )
    default_shell_windows_custom = models.CharField(
        max_length=512, blank=True, default=""
    )

    default_shell_linux = models.CharField(
        max_length=32,
        choices=LinuxTerminalShellChoices.choices,
        default=LinuxTerminalShellChoices.BASH,
    )
    default_shell_linux_custom = models.CharField(
        max_length=512, blank=True, default=""
    )

    default_shell_darwin = models.CharField(
        max_length=32,
        choices=DarwinTerminalShellChoices.choices,
        default=DarwinTerminalShellChoices.BASH,
    )
    default_shell_darwin_custom = models.CharField(
        max_length=512, blank=True, default=""
    )
    terminal_mode = models.CharField(
        max_length=20,
        choices=TerminalModeChoices.choices,
        default=TerminalModeChoices.NEW,
    )

    def save(self, *args, **kwargs) -> None:
        from alerts.tasks import cache_agents_alert_template

        cache.delete(CORESETTINGS_CACHE_KEY)

        if not self.pk and CoreSettings.objects.exists():
            raise ValidationError("There can only be one CoreSettings instance")

        # for install script
        if not self.pk:
            with suppress(Exception):
                self.mesh_site = settings.MESH_SITE
                self.mesh_username = settings.MESH_USERNAME.lower()
                self.mesh_token = settings.MESH_TOKEN_KEY

        old_settings = type(self).objects.get(pk=self.pk) if self.pk else None

        if old_settings:
            # fail safe to not lock out user logons
            if not self.sso_enabled and self.block_local_user_logon:
                self.block_local_user_logon = False

            if old_settings.sso_enabled != self.sso_enabled and self.sso_enabled:
                from core.utils import token_is_valid

                _, valid = token_is_valid()
                if not valid:
                    raise ValidationError("")

        super().save(*args, **kwargs)

        if old_settings:

            if (
                old_settings.alert_template != self.alert_template
                or old_settings.server_policy != self.server_policy
                or old_settings.workstation_policy != self.workstation_policy
            ):
                cache_agents_alert_template.delay()

            if old_settings.workstation_policy != self.workstation_policy:
                cache.delete_many_pattern("site_workstation_*")

            if old_settings.server_policy != self.server_policy:
                cache.delete_many_pattern("site_server_*")

            if (
                old_settings.server_policy != self.server_policy
                or old_settings.workstation_policy != self.workstation_policy
            ):
                cache.delete_many_pattern("agent_*")

    def __str__(self) -> str:
        return "Global Site Settings"

    @property
    def mesh_api_superuser(self) -> str:
        # must be lowercase otherwise mesh api breaks
        return self.mesh_username.lower()

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

    @property
    def server_scripts_enabled(self) -> bool:
        if (
            getattr(settings, "HOSTED", False)
            or getattr(settings, "TRMM_DISABLE_SERVER_SCRIPTS", False)
            or getattr(settings, "DEMO", False)
        ):
            return False

        return self.enable_server_scripts

    @property
    def web_terminal_enabled(self) -> bool:
        if (
            getattr(settings, "HOSTED", False)
            or getattr(settings, "TRMM_DISABLE_WEB_TERMINAL", False)
            or getattr(settings, "DEMO", False)
        ):
            return False

        return self.enable_server_webterminal

    def send_mail(
        self,
        subject: str,
        body: str,
        attachment: Optional[bytes] = None,
        attachment_filename: Optional[str] = None,
        attachment_type: Optional[str] = None,
        attachment_extension: Optional[str] = None,
        alert_template: "Optional[AlertTemplate]" = None,
        override_recipients: Optional[List[str]] = [],
        override_from: Optional[str] = None,
        override_from_name: Optional[str] = None,
        test: bool = False,
    ) -> tuple[str, bool]:
        if test and not self.email_is_configured:
            return "There needs to be at least one email recipient configured", False
        # return since email must be configured to continue
        elif not self.email_is_configured:
            return "SMTP messaging not configured.", False

        # override email from: explicit override wins, then alert_template, then
        # the configured SMTP from address.
        if override_from:
            from_address = override_from
        elif alert_template and alert_template.email_from:
            from_address = alert_template.email_from
        else:
            from_address = self.smtp_from_email

        # override email recipients if alert_template is passed and is set
        if override_recipients:
            email_recipients = ", ".join(override_recipients)
        elif alert_template and alert_template.email_recipients:
            email_recipients = ", ".join(alert_template.email_recipients)
        elif self.email_alert_recipients:
            email_recipients = ", ".join(self.email_alert_recipients)
        else:
            return "There needs to be at least one email recipient configured", False

        try:
            msg = EmailMessage()

            msg["Subject"] = subject
            msg["Date"] = formatdate(localtime=True)

            display_name = (
                override_from_name
                if override_from_name is not None
                else self.smtp_from_name
            )
            if display_name:
                msg["From"] = Address(
                    display_name=display_name, addr_spec=from_address
                )
            else:
                msg["From"] = from_address

            msg["To"] = email_recipients
            msg.set_content(body)

            if attachment:
                match attachment_type:
                    case "pdf":
                        subtype = "pdf"
                        ext = "pdf"
                    case "html":
                        subtype = "html"
                        ext = "html"
                    case "plaintext":
                        subtype = "plain"
                        ext = attachment_extension or "txt"
                    case _:
                        subtype = "plain"
                        ext = "txt"

                if attachment_type == "pdf":
                    msg.add_attachment(
                        attachment,
                        maintype="application",
                        subtype=subtype,
                        filename=f"{attachment_filename}.{ext}",
                    )
                elif attachment_type in ("html", "plaintext"):
                    msg.add_attachment(
                        attachment,
                        subtype=subtype,
                        filename=f"{attachment_filename}.{ext}",
                    )

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
                    # gmail smtp relay specific handling.
                    if self.smtp_host == "smtp-relay.gmail.com":
                        server.ehlo()
                        server.starttls()
                        server.send_message(msg)
                        server.quit()
                    else:
                        # smtp relay. no auth required
                        server.send_message(msg)
                        server.quit()

        except Exception as e:
            logger.error(traceback.format_exc())
            DebugLog.error(message=f"Sending email failed with error: {e}")
            if test:
                return str(e), False

        if test:
            return "Email test ok!", True

        return "ok", True

    def send_sms(
        self,
        body: str,
        alert_template: "Optional[AlertTemplate]" = None,
        test: bool = False,
    ) -> tuple[str, bool]:
        if not self.sms_is_configured:
            return "Sms alerting is not setup correctly.", False

        # override email recipients if alert_template is passed and is set
        if alert_template and alert_template.text_recipients:
            text_recipients = alert_template.text_recipients
        elif self.sms_alert_recipients:
            text_recipients = cast(List[str], self.sms_alert_recipients)
        else:
            return "No sms recipients found", False

        tw_client = TwClient(self.twilio_account_sid, self.twilio_auth_token)
        for num in text_recipients:
            try:
                tw_client.messages.create(body=body, to=num, from_=self.twilio_number)
            except TwilioRestException as e:
                DebugLog.error(message=f"SMS failed to send: {e}")
                if test:
                    return str(e), False

        if test:
            return "SMS Test sent successfully!", True

        return "ok", True

    @staticmethod
    def serialize(core):
        # serializes the core and returns json
        from .serializers import CoreSerializer

        return CoreSerializer(core).data


class CustomField(BaseAuditModel):
    order = models.PositiveIntegerField(default=0)
    model = models.CharField(max_length=25, choices=CustomFieldModel.choices)
    type = models.CharField(
        max_length=25, choices=CustomFieldType.choices, default=CustomFieldType.TEXT
    )
    options = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    name = models.CharField(max_length=100)
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
    hide_in_summary = models.BooleanField(default=False)

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
        if self.type == CustomFieldType.MULTIPLE:
            return self.default_values_multiple
        elif self.type == CustomFieldType.CHECKBOX:
            return self.default_value_bool

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
    token: str = models.CharField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and CodeSignToken.objects.exists():
            raise ValidationError("There can only be one CodeSignToken instance")

        super().save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        if not self.token:
            return False

        try:
            r = requests.post(
                settings.CHECK_TOKEN_URL,
                json={"token": self.token, "api": settings.ALLOWED_HOSTS[0]},
                headers={"Content-type": "application/json"},
                timeout=15,
            )
        except:
            return False

        return r.status_code == 200

    @property
    def is_expired(self) -> bool:
        if not self.token:
            return False

        try:
            r = requests.post(
                settings.CHECK_TOKEN_URL,
                json={"token": self.token, "api": settings.ALLOWED_HOSTS[0]},
                headers={"Content-type": "application/json"},
                timeout=15,
            )
        except:
            return False

        return r.status_code == 401

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
    name = models.CharField(max_length=255)
    desc = models.TextField(null=True, blank=True)
    pattern = models.TextField()
    action_type = models.CharField(
        max_length=10, choices=URLActionType.choices, default=URLActionType.WEB
    )
    rest_method = models.CharField(
        max_length=10,
        choices=URLActionRestMethod.choices,
        default=URLActionRestMethod.POST,
    )
    rest_body = models.TextField(null=True, blank=True, default="")
    rest_headers = models.TextField(null=True, blank=True, default="")

    def __str__(self):
        return self.name

    @staticmethod
    def serialize(action):
        from .serializers import URLActionSerializer

        return URLActionSerializer(action).data


class Schedule(BaseAuditModel):
    name = models.CharField(max_length=255)
    run_time = models.TimeField()
    run_time_weekdays = ArrayField(
        base_field=models.PositiveSmallIntegerField(),
        size=7,
        blank=True,
        null=True,
        default=list,
    )

    monthly_months_of_year = ArrayField(
        base_field=models.PositiveSmallIntegerField(),
        size=12,
        blank=True,
        null=True,
        default=list,
    )

    # 1-31 days. last day of month is 32
    monthly_days_of_month = ArrayField(
        base_field=models.PositiveIntegerField(),
        size=32,
        blank=True,
        null=True,
        default=list,
    )

    # 1st-4th weeks of month. Last week of month is 5
    monthly_weeks_of_month = ArrayField(
        base_field=models.PositiveSmallIntegerField(),
        size=6,
        blank=True,
        null=True,
        default=list,
    )
    schedule_type = models.CharField(
        max_length=15, choices=ScheduleType.choices, default=ScheduleType.WEEKLY
    )
    monthly_type = models.CharField(
        max_length=15, choices=MonthlyType.choices, default=MonthlyType.DAYS
    )

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def serialize(schedule):
        from .serializers import ScheduleAuditSerializer

        return ScheduleAuditSerializer(schedule).data


class AIProvider(BaseAuditModel):
    PROVIDER_CHOICES = [
        ("anthropic", "Anthropic"),
        ("openai", "OpenAI"),
        ("google", "Google"),
        ("xai", "xAI"),
        ("openrouter", "OpenRouter"),
        ("custom", "Custom (OpenAI-compatible)"),
    ]
    name = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True)
    api_key = models.CharField(max_length=500, blank=True, default="")
    base_url = models.CharField(max_length=500, blank=True, default="")
    enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.get_name_display()

    @staticmethod
    def serialize(obj):
        from .serializers import AIProviderSerializer

        return AIProviderSerializer(obj).data


class AIModel(BaseAuditModel):
    provider = models.ForeignKey(
        "core.AIProvider", related_name="models", on_delete=models.CASCADE
    )
    model_id = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    thinking_level = models.CharField(max_length=20, blank=True, default="medium")
    enabled = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ("provider", "model_id")

    def __str__(self) -> str:
        return f"{self.display_name} ({self.provider.name}/{self.model_id})"

    def save(self, *args, **kwargs) -> None:
        # only one default model globally
        if self.is_default:
            AIModel.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @staticmethod
    def serialize(obj):
        from .serializers import AIModelSerializer

        return AIModelSerializer(obj).data


class AITask(BaseAuditModel):
    SCHEDULE_INTERVAL = "interval"
    SCHEDULE_DAILY = "daily"
    SCHEDULE_WEEKLY = "weekly"
    SCHEDULE_MONTHLY = "monthly"
    SCHEDULE_ONCE = "once"
    SCHEDULE_CHOICES = [
        (SCHEDULE_INTERVAL, "Interval"),
        (SCHEDULE_DAILY, "Daily"),
        (SCHEDULE_WEEKLY, "Weekly"),
        (SCHEDULE_MONTHLY, "Monthly"),
        (SCHEDULE_ONCE, "One time"),
    ]

    THRESHOLD_CHOICES = [
        ("never", "Never alert"),
        ("warning", "Alert on Warning or Alert"),
        ("alert", "Alert only on Alert"),
    ]

    name = models.CharField(max_length=255)
    agent = models.ForeignKey(
        "agents.Agent", related_name="ai_tasks", on_delete=models.CASCADE
    )
    prompt = models.TextField()
    model = models.ForeignKey(
        "core.AIModel", null=True, blank=True, on_delete=models.SET_NULL
    )
    enabled = models.BooleanField(default=True)
    allow_mutating = models.BooleanField(default=False)

    # run mode: "now" = one-shot (disables after run), "schedule" = recurring
    run_mode = models.CharField(max_length=20, default="schedule")  # now|schedule
    schedule_type = models.CharField(
        max_length=20, choices=SCHEDULE_CHOICES, default=SCHEDULE_INTERVAL
    )
    interval_minutes = models.PositiveIntegerField(default=60)
    run_time = models.TimeField(null=True, blank=True)  # daily/weekly/monthly/once
    weekly_days = ArrayField(  # 0=Mon .. 6=Sun
        base_field=models.PositiveSmallIntegerField(),
        size=7,
        null=True,
        blank=True,
        default=list,
    )
    monthly_day = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-31
    run_at = models.DateTimeField(null=True, blank=True)  # computed target for one-time
    next_run = models.DateTimeField(null=True, blank=True)  # computed for recurring

    alert_threshold = models.CharField(
        max_length=20, choices=THRESHOLD_CHOICES, default="alert"
    )

    # result of the most recent run
    last_run = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=20, null=True, blank=True)  # ok/warning/alert/error
    last_summary = models.TextField(null=True, blank=True)
    last_output = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.agent.hostname})"

    @staticmethod
    def serialize(obj):
        from .serializers import AITaskSerializer

        return AITaskSerializer(obj).data


class AITaskRun(models.Model):
    # a run belongs to either a scheduled task or a bulk command; agent is always set
    task = models.ForeignKey(
        "core.AITask", related_name="runs", on_delete=models.CASCADE, null=True, blank=True
    )
    bulk = models.ForeignKey(
        "core.BulkAICommand", related_name="runs", on_delete=models.CASCADE, null=True, blank=True
    )
    agent = models.ForeignKey(
        "agents.Agent", related_name="ai_runs", on_delete=models.CASCADE, null=True, blank=True
    )
    run_id = models.CharField(max_length=64, unique=True)  # correlates live progress
    # groups all per-machine runs of a single bulk dispatch, so a finalizer can
    # compile ONE combined report after the whole batch finishes.
    batch_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    triggered_by = models.CharField(max_length=20, default="schedule")  # schedule|manual|bulk
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="running")  # running/ok/warning/alert/error
    summary = models.TextField(null=True, blank=True)
    output = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    @property
    def source(self) -> str:
        if self.bulk_id:
            return "bulk"
        if self.task_id:
            return "task"
        return "chat"

    @property
    def source_name(self) -> str:
        if self.bulk_id:
            return self.bulk.name
        if self.task_id:
            return self.task.name
        return ""

    def get_agent(self):
        if self.agent_id:
            return self.agent
        if self.task_id:
            return self.task.agent
        return None

    def __str__(self) -> str:
        return f"{self.source_name} @ {self.started_at} [{self.status}]"


class BulkAICommand(BaseAuditModel):
    SCHED_INTERVAL = "interval"
    SCHED_DAILY = "daily"
    SCHED_WEEKLY = "weekly"
    SCHED_MONTHLY = "monthly"
    SCHED_CHOICES = [
        (SCHED_INTERVAL, "Every N hours"),
        (SCHED_DAILY, "Daily"),
        (SCHED_WEEKLY, "Weekly"),
        (SCHED_MONTHLY, "Monthly"),
    ]
    THRESHOLD_CHOICES = [
        ("never", "Never alert"),
        ("warning", "Alert on Warning or Alert"),
        ("alert", "Alert only on Alert"),
    ]

    name = models.CharField(max_length=255)
    prompt = models.TextField()
    # Optional: when set, after the whole batch finishes a single finalizer run
    # compiles ONE combined report (given every machine's result) following this
    # instruction + the HELPDESK POLICY. Empty = no combined report.
    report_prompt = models.TextField(blank=True, default="")
    model = models.ForeignKey(
        "core.AIModel", null=True, blank=True, on_delete=models.SET_NULL
    )
    enabled = models.BooleanField(default=True)
    allow_mutating = models.BooleanField(default=False)
    alert_threshold = models.CharField(
        max_length=20, choices=THRESHOLD_CHOICES, default="alert"
    )

    # run mode: "now" = one-shot (disables itself after running), "schedule" = recurring
    run_mode = models.CharField(max_length=20, default="schedule")  # now|schedule
    # schedule
    schedule_type = models.CharField(
        max_length=20, choices=SCHED_CHOICES, default=SCHED_INTERVAL
    )
    interval_hours = models.PositiveIntegerField(default=24)
    run_time = models.TimeField(null=True, blank=True)  # daily/weekly/monthly
    weekly_days = ArrayField(  # 0=Mon .. 6=Sun
        base_field=models.PositiveSmallIntegerField(),
        size=7,
        null=True,
        blank=True,
        default=list,
    )
    monthly_day = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-31
    next_run = models.DateTimeField(null=True, blank=True)

    # targets (mirrors bulk command); target also supports "filter"
    target = models.CharField(max_length=20, default="all")  # all/client/site/agents/filter
    # dynamic filter rules for target=="filter". New shape: a list of GROUPS,
    # each {match: "all"|"any", conditions: [{field, op, value}, ...]}. Old shape
    # (a flat list of {field, op, value}) is still accepted and treated as one
    # AND group. Groups are combined using filter_match below.
    filters = models.JSONField(default=list, blank=True)
    # how to combine the filter GROUPS: "all" = AND, "any" = OR.
    filter_match = models.CharField(max_length=8, default="any")
    # agent_ids explicitly excluded from the resolved target set, even if they
    # match the filter/client/site/all selection.
    exclude_agent_ids = models.JSONField(default=list, blank=True)
    client = models.ForeignKey(
        "clients.Client", null=True, blank=True, on_delete=models.SET_NULL
    )
    site = models.ForeignKey(
        "clients.Site", null=True, blank=True, on_delete=models.SET_NULL
    )
    agents = models.ManyToManyField("agents.Agent", blank=True, related_name="bulk_ai_commands")
    mon_type = models.CharField(max_length=20, default="all")  # all/servers/workstations
    os_type = models.CharField(max_length=20, default="all")  # all/windows/linux/darwin

    # results
    last_run = models.DateTimeField(null=True, blank=True)
    last_run_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def serialize(obj):
        from .serializers import BulkAICommandSerializer

        return BulkAICommandSerializer(obj).data
