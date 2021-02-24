from django.contrib.postgres.fields import ArrayField
from django.db import models
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
    email_sent = models.DateTimeField(null=True, blank=True)
    resolved_email_sent = models.DateTimeField(null=True, blank=True)
    sms_sent = models.DateTimeField(null=True, blank=True)
    resolved_sms_sent = models.DateTimeField(null=True, blank=True)
    hidden = models.BooleanField(default=False)
    action_run = models.DateTimeField(null=True, blank=True)
    action_stdout = models.TextField(null=True, blank=True)
    action_stderr = models.TextField(null=True, blank=True)
    action_retcode = models.IntegerField(null=True, blank=True)
    action_execution_time = models.CharField(max_length=100, null=True, blank=True)
    resolved_action_run = models.DateTimeField(null=True, blank=True)
    resolved_action_stdout = models.TextField(null=True, blank=True)
    resolved_action_stderr = models.TextField(null=True, blank=True)
    resolved_action_retcode = models.IntegerField(null=True, blank=True)
    resolved_action_execution_time = models.CharField(
        max_length=100, null=True, blank=True
    )

    def __str__(self):
        return self.message

    def resolve(self):
        self.resolved = True
        self.resolved_on = djangotime.now()
        self.snoozed = False
        self.snooze_until = None
        self.save()

    @classmethod
    def create_availability_alert(cls, agent):
        if not cls.objects.filter(agent=agent, resolved=False).exists():
            return cls.objects.create(
                agent=agent,
                alert_type="availability",
                severity="error",
                message=f"{agent.hostname} in {agent.client.name}\\{agent.site.name} is overdue.",
                hidden=True,
            )

    @classmethod
    def create_check_alert(cls, check):

        if not cls.objects.filter(assigned_check=check, resolved=False).exists():
            return cls.objects.create(
                assigned_check=check,
                alert_type="check",
                severity=check.alert_severity,
                message=f"{check.agent.hostname} has a {check.check_type} check: {check.readable_desc} that failed.",
                hidden=True,
            )

    @classmethod
    def create_task_alert(cls, task):

        if not cls.objects.filter(assigned_task=task, resolved=False).exists():
            return cls.objects.create(
                assigned_task=task,
                alert_type="task",
                severity=task.alert_severity,
                message=f"{task.agent.hostname} has task: {task.name} that failed.",
                hidden=True,
            )


class AlertTemplate(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    action = models.ForeignKey(
        "scripts.Script",
        related_name="alert_template",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    action_args = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    action_timeout = models.PositiveIntegerField(default=15)
    resolved_action = models.ForeignKey(
        "scripts.Script",
        related_name="resolved_alert_template",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    resolved_action_args = ArrayField(
        models.CharField(max_length=255, null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )
    resolved_action_timeout = models.PositiveIntegerField(default=15)

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
    agent_always_email = BooleanField(null=True, blank=True, default=None)
    agent_always_text = BooleanField(null=True, blank=True, default=None)
    agent_always_alert = BooleanField(null=True, blank=True, default=None)
    agent_periodic_alert_days = PositiveIntegerField(blank=True, null=True, default=0)

    # check alert settings
    check_email_alert_severity = ArrayField(
        models.CharField(max_length=25, blank=True, choices=SEVERITY_CHOICES),
        blank=True,
        default=list,
    )
    check_text_alert_severity = ArrayField(
        models.CharField(max_length=25, blank=True, choices=SEVERITY_CHOICES),
        blank=True,
        default=list,
    )
    check_dashboard_alert_severity = ArrayField(
        models.CharField(max_length=25, blank=True, choices=SEVERITY_CHOICES),
        blank=True,
        default=list,
    )
    check_email_on_resolved = BooleanField(null=True, blank=True, default=False)
    check_text_on_resolved = BooleanField(null=True, blank=True, default=False)
    check_always_email = BooleanField(null=True, blank=True, default=None)
    check_always_text = BooleanField(null=True, blank=True, default=None)
    check_always_alert = BooleanField(null=True, blank=True, default=None)
    check_periodic_alert_days = PositiveIntegerField(blank=True, null=True, default=0)

    # task alert settings
    task_email_alert_severity = ArrayField(
        models.CharField(max_length=25, blank=True, choices=SEVERITY_CHOICES),
        blank=True,
        default=list,
    )
    task_text_alert_severity = ArrayField(
        models.CharField(max_length=25, blank=True, choices=SEVERITY_CHOICES),
        blank=True,
        default=list,
    )
    task_dashboard_alert_severity = ArrayField(
        models.CharField(max_length=25, blank=True, choices=SEVERITY_CHOICES),
        blank=True,
        default=list,
    )
    task_email_on_resolved = BooleanField(null=True, blank=True, default=False)
    task_text_on_resolved = BooleanField(null=True, blank=True, default=False)
    task_always_email = BooleanField(null=True, blank=True, default=None)
    task_always_text = BooleanField(null=True, blank=True, default=None)
    task_always_alert = BooleanField(null=True, blank=True, default=None)
    task_periodic_alert_days = PositiveIntegerField(blank=True, null=True, default=0)

    # exclusion settings
    exclude_workstations = BooleanField(null=True, blank=True, default=False)
    exclude_servers = BooleanField(null=True, blank=True, default=False)

    excluded_sites = models.ManyToManyField(
        "clients.Site", related_name="alert_exclusions", blank=True
    )
    excluded_clients = models.ManyToManyField(
        "clients.Client", related_name="alert_exclusions", blank=True
    )
    excluded_agents = models.ManyToManyField(
        "agents.Agent", related_name="alert_exclusions", blank=True
    )

    def __str__(self):
        return self.name

    @property
    def has_agent_settings(self) -> bool:
        return (
            self.agent_email_on_resolved
            or self.agent_text_on_resolved
            or self.agent_always_email
            or self.agent_always_text
            or self.agent_always_alert
            or bool(self.agent_periodic_alert_days)
        )

    @property
    def has_check_settings(self) -> bool:
        return (
            bool(self.check_email_alert_severity)
            or bool(self.check_text_alert_severity)
            or bool(self.check_dashboard_alert_severity)
            or self.check_email_on_resolved
            or self.check_text_on_resolved
            or self.check_always_email
            or self.check_always_text
            or self.check_always_alert
            or bool(self.check_periodic_alert_days)
        )

    @property
    def has_task_settings(self) -> bool:
        return (
            bool(self.task_email_alert_severity)
            or bool(self.task_text_alert_severity)
            or bool(self.task_dashboard_alert_severity)
            or self.task_email_on_resolved
            or self.task_text_on_resolved
            or self.task_always_email
            or self.task_always_text
            or self.task_always_alert
            or bool(self.task_periodic_alert_days)
        )

    @property
    def has_core_settings(self) -> bool:
        return bool(self.email_from) or self.email_recipients or self.text_recipients

    @property
    def is_default_template(self) -> bool:
        return self.default_alert_template.exists()  # type: ignore
