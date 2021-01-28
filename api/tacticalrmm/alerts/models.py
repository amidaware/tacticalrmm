from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.fields import BooleanField, PositiveIntegerField
from django.utils import timezone as djangotime

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
    resolved_on = models.DateTimeField(null=True, blank=True)
    severity = models.CharField(max_length=30, choices=SEVERITY_CHOICES, default="info")

    def __str__(self):
        return self.message

    def resolve(self):
        self.resolved = True
        self.resolved_on = djangotime.now()
        self.snoozed = False
        self.snoozed_until = None
        self.save()

    @classmethod
    def create_availability_alert(cls, agent, severity="error") -> None:
        if not cls.objects.filter(agent=agent, resolved=False).exists():
            cls.objects.create(
                agent=agent,
                alert_type="availability",
                severity=severity,
                message=f"{agent.hostname} in {agent.client.name}\{agent.site.name} is Offline.",
            )

    @classmethod
    def create_check_alert(cls, check, severity="error") -> None:

        if not cls.objects.filter(assigned_check=check, resolved=False).exists():
            cls.objects.create(
                assigned_check=check,
                agent=check.agent,
                alert_type="check",
                severity=severity,
                message=f"{check.agent.hostname} has {check.check_type} check that failed.",
            )

    @classmethod
    def create_task_alert(cls, task, severity="error") -> None:

        if not cls.objects.filter(assigned_task=task, resolved=False).exists():
            cls.objects.create(
                assigned_task=task,
                agent=task.agent,
                alert_type="task",
                severity=severity,
                message=f"{task.agent.hostname} has task that failed.",
            )

    @classmethod
    def create_custom_alert(cls, custom):
        pass


class AlertTemplate(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

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

    # agent alert settings
    agent_email_on_resolved = BooleanField(null=True, blank=True, default=False)
    agent_text_on_resolved = BooleanField(null=True, blank=True, default=False)
    agent_include_desktops = BooleanField(null=True, blank=True, default=False)
    agent_always_email = BooleanField(null=True, blank=True, default=False)
    agent_always_text = BooleanField(null=True, blank=True, default=False)
    agent_periodic_alert_days = PositiveIntegerField(blank=True, null=True, default=0)

    # check alert settings
    check_email_alert_severity = ArrayField(
        models.CharField(
            max_length=25, blank=True, null=True, choices=SEVERITY_CHOICES
        ),
        null=True,
        blank=True,
        default=list,
    )
    check_text_alert_severity = ArrayField(
        models.CharField(
            max_length=25, blank=True, null=True, choices=SEVERITY_CHOICES
        ),
        null=True,
        blank=True,
        default=list,
    )
    check_email_on_resolved = BooleanField(null=True, blank=True, default=False)
    check_text_on_resolved = BooleanField(null=True, blank=True, default=False)
    check_include_desktops = BooleanField(null=True, blank=True, default=False)
    check_always_email = BooleanField(null=True, blank=True, default=False)
    check_always_text = BooleanField(null=True, blank=True, default=False)
    check_periodic_alert_days = PositiveIntegerField(blank=True, null=True, default=0)

    # task alert settings
    task_email_alert_severity = ArrayField(
        models.CharField(
            max_length=25, blank=True, null=True, choices=SEVERITY_CHOICES
        ),
        null=True,
        blank=True,
        default=list,
    )
    task_text_alert_severity = ArrayField(
        models.CharField(
            max_length=25, blank=True, null=True, choices=SEVERITY_CHOICES
        ),
        null=True,
        blank=True,
        default=list,
    )
    task_email_on_resolved = BooleanField(null=True, blank=True, default=False)
    task_text_on_resolved = BooleanField(null=True, blank=True, default=False)
    task_include_desktops = BooleanField(null=True, blank=True, default=False)
    task_always_email = BooleanField(null=True, blank=True, default=False)
    task_always_text = BooleanField(null=True, blank=True, default=False)
    task_periodic_alert_days = PositiveIntegerField(blank=True, null=True, default=0)

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
