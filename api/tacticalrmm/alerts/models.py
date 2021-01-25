from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.fields import BooleanField

SEVERITY_CHOICES = [
    ("info", "Informational"),
    ("warning", "Warning"),
    ("error", "Error"),
]

ALERT_TYPE_CHOICES = [
    ("availability", "Availability"),
    ("check", "Check"),
    ("task", "Task"),
    ("custom", "Custom"),
]


class Alert(models.Model):
    agent = models.ForeignKey(
        "agents.Agent",
        related_name="agent",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    assigned_check = models.ForeignKey(
        "checks.Check",
        related_name="alert",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    assigned_task = models.ForeignKey(
        "autotasks.AutomatedTask",
        related_name="alert",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    alert_type = models.CharField(
        max_length=20, choices=ALERT_TYPE_CHOICES, default="availability"
    )
    message = models.TextField(null=True, blank=True)
    alert_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    snoozed = models.BooleanField(default=False)
    snooze_until = models.DateTimeField(null=True, blank=True)
    resolved = models.BooleanField(default=False)
    resolved_time = models.DateTimeField(null=True, blank=True)
    severity = models.CharField(
        max_length=100, choices=SEVERITY_CHOICES, default="info"
    )

    def __str__(self):
        return self.message

    @classmethod
    def create_availability_alert(cls, agent):
        pass

    @classmethod
    def create_check_alert(cls, check):
        pass

    @classmethod
    def create_task_alert(cls, task):
        pass

    @classmethod
    def create_custom_alert(cls, custom):
        pass


class AlertTemplate(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    actions = models.ManyToManyField(
        "scripts.Script", related_name="alert_templates", blank=True
    )

    # ignores setting on agent
    always_email = models.BooleanField(default=False)
    always_text = models.BooleanField(default=False)

    # overrides the global recipients
    email_recipients = ArrayField(
        models.CharField(max_length=100, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    text_recipients = ArrayField(
        models.CharField(max_length=100, blank=True),
        null=True,
        blank=True,
        default=list,
    )

    # overrides the from address
    email_from = models.EmailField(blank=True, null=True)

    # will only email/text on a specific severity
    email_alert_severity = ArrayField(
        models.CharField(
            max_length=25, blank=True, null=True, choices=SEVERITY_CHOICES
        ),
        null=True,
        blank=True,
        default=list,
    )
    text_alert_severity = ArrayField(
        models.CharField(
            max_length=25, blank=True, null=True, choices=SEVERITY_CHOICES
        ),
        null=True,
        blank=True,
        default=list,
    )

    email_on_resolved = BooleanField(default=False)
    text_on_resolved = BooleanField(default=False)

    def __str__(self):
        return self.name


class AlertExclusion(models.Model):
    alert_template = models.ForeignKey(
        "AlertTemplate",
        related_name="alert",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    policies = models.ManyToManyField(
        "automation.Policy", related_name="alert_exclusions"
    )
    sites = models.ManyToManyField(
        "clients.Site",
        related_name="alert_exclusions",
    )
    clients = models.ManyToManyField(
        "clients.Client",
        related_name="alert_exclusions",
    )

    def __str__(self):
        return f"Alert Exclusions for {self.alert_template.name}"
