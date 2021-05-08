from __future__ import annotations

import re
from typing import TYPE_CHECKING, Union

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.fields import BooleanField, PositiveIntegerField
from django.utils import timezone as djangotime
from loguru import logger

if TYPE_CHECKING:
    from agents.models import Agent
    from autotasks.models import AutomatedTask
    from checks.models import Check

logger.configure(**settings.LOG_CONFIG)

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
    def create_or_return_availability_alert(cls, agent):
        if not cls.objects.filter(agent=agent, resolved=False).exists():
            return cls.objects.create(
                agent=agent,
                alert_type="availability",
                severity="error",
                message=f"{agent.hostname} in {agent.client.name}\\{agent.site.name} is overdue.",
                hidden=True,
            )
        else:
            return cls.objects.get(agent=agent, resolved=False)

    @classmethod
    def create_or_return_check_alert(cls, check):

        if not cls.objects.filter(assigned_check=check, resolved=False).exists():
            return cls.objects.create(
                assigned_check=check,
                alert_type="check",
                severity=check.alert_severity,
                message=f"{check.agent.hostname} has a {check.check_type} check: {check.readable_desc} that failed.",
                hidden=True,
            )
        else:
            return cls.objects.get(assigned_check=check, resolved=False)

    @classmethod
    def create_or_return_task_alert(cls, task):

        if not cls.objects.filter(assigned_task=task, resolved=False).exists():
            return cls.objects.create(
                assigned_task=task,
                alert_type="task",
                severity=task.alert_severity,
                message=f"{task.agent.hostname} has task: {task.name} that failed.",
                hidden=True,
            )
        else:
            return cls.objects.get(assigned_task=task, resolved=False)

    @classmethod
    def handle_alert_failure(cls, instance: Union[Agent, AutomatedTask, Check]) -> None:
        from agents.models import Agent
        from autotasks.models import AutomatedTask
        from checks.models import Check

        # set variables
        dashboard_severities = None
        email_severities = None
        text_severities = None
        always_dashboard = None
        always_email = None
        always_text = None
        alert_interval = None
        email_task = None
        text_task = None

        # check what the instance passed is
        if isinstance(instance, Agent):
            from agents.tasks import agent_outage_email_task, agent_outage_sms_task

            email_task = agent_outage_email_task
            text_task = agent_outage_sms_task

            email_alert = instance.overdue_email_alert
            text_alert = instance.overdue_text_alert
            dashboard_alert = instance.overdue_dashboard_alert
            alert_template = instance.alert_template
            maintenance_mode = instance.maintenance_mode
            alert_severity = "error"
            agent = instance

            # set alert_template settings
            if alert_template:
                dashboard_severities = ["error"]
                email_severities = ["error"]
                text_severities = ["error"]
                always_dashboard = alert_template.agent_always_alert
                always_email = alert_template.agent_always_email
                always_text = alert_template.agent_always_text
                alert_interval = alert_template.agent_periodic_alert_days

            if instance.should_create_alert(alert_template):
                alert = cls.create_or_return_availability_alert(instance)
            else:
                # check if there is an alert that exists
                if cls.objects.filter(agent=instance, resolved=False).exists():
                    alert = cls.objects.get(agent=instance, resolved=False)
                else:
                    alert = None

        elif isinstance(instance, Check):
            from checks.tasks import (
                handle_check_email_alert_task,
                handle_check_sms_alert_task,
            )

            email_task = handle_check_email_alert_task
            text_task = handle_check_sms_alert_task

            email_alert = instance.email_alert
            text_alert = instance.text_alert
            dashboard_alert = instance.dashboard_alert
            alert_template = instance.agent.alert_template
            maintenance_mode = instance.agent.maintenance_mode
            alert_severity = instance.alert_severity
            agent = instance.agent

            # set alert_template settings
            if alert_template:
                dashboard_severities = alert_template.check_dashboard_alert_severity
                email_severities = alert_template.check_email_alert_severity
                text_severities = alert_template.check_text_alert_severity
                always_dashboard = alert_template.check_always_alert
                always_email = alert_template.check_always_email
                always_text = alert_template.check_always_text
                alert_interval = alert_template.check_periodic_alert_days

            if instance.should_create_alert(alert_template):
                alert = cls.create_or_return_check_alert(instance)
            else:
                # check if there is an alert that exists
                if cls.objects.filter(assigned_check=instance, resolved=False).exists():
                    alert = cls.objects.get(assigned_check=instance, resolved=False)
                else:
                    alert = None

        elif isinstance(instance, AutomatedTask):
            from autotasks.tasks import handle_task_email_alert, handle_task_sms_alert

            email_task = handle_task_email_alert
            text_task = handle_task_sms_alert

            email_alert = instance.email_alert
            text_alert = instance.text_alert
            dashboard_alert = instance.dashboard_alert
            alert_template = instance.agent.alert_template
            maintenance_mode = instance.agent.maintenance_mode
            alert_severity = instance.alert_severity
            agent = instance.agent

            # set alert_template settings
            if alert_template:
                dashboard_severities = alert_template.task_dashboard_alert_severity
                email_severities = alert_template.task_email_alert_severity
                text_severities = alert_template.task_text_alert_severity
                always_dashboard = alert_template.task_always_alert
                always_email = alert_template.task_always_email
                always_text = alert_template.task_always_text
                alert_interval = alert_template.task_periodic_alert_days

            if instance.should_create_alert(alert_template):
                alert = cls.create_or_return_task_alert(instance)
            else:
                # check if there is an alert that exists
                if cls.objects.filter(assigned_task=instance, resolved=False).exists():
                    alert = cls.objects.get(assigned_task=instance, resolved=False)
                else:
                    alert = None
        else:
            return

        # return if agent is in maintenance mode
        if maintenance_mode or not alert:
            return

        # check if alert severity changed on check and update the alert
        if alert_severity != alert.severity:
            alert.severity = alert_severity
            alert.save(update_fields=["severity"])

        # create alert in dashboard if enabled
        if dashboard_alert or always_dashboard:

            # check if alert template is set and specific severities are configured
            if alert_template and alert.severity not in dashboard_severities:  # type: ignore
                pass
            else:
                alert.hidden = False
                alert.save()

        # send email if enabled
        if email_alert or always_email:

            # check if alert template is set and specific severities are configured
            if alert_template and alert.severity not in email_severities:  # type: ignore
                pass
            else:
                email_task.delay(
                    pk=alert.pk,
                    alert_interval=alert_interval,
                )

        # send text if enabled
        if text_alert or always_text:

            # check if alert template is set and specific severities are configured
            if alert_template and alert.severity not in text_severities:  # type: ignore
                pass
            else:
                text_task.delay(pk=alert.pk, alert_interval=alert_interval)

        # check if any scripts should be run
        if alert_template and alert_template.action and not alert.action_run:
            r = agent.run_script(
                scriptpk=alert_template.action.pk,
                args=alert.parse_script_args(alert_template.action_args),
                timeout=alert_template.action_timeout,
                wait=True,
                full=True,
                run_on_any=True,
            )

            # command was successful
            if type(r) == dict:
                alert.action_retcode = r["retcode"]
                alert.action_stdout = r["stdout"]
                alert.action_stderr = r["stderr"]
                alert.action_execution_time = "{:.4f}".format(r["execution_time"])
                alert.action_run = djangotime.now()
                alert.save()
            else:
                logger.error(
                    f"Failure action: {alert_template.action.name} failed to run on any agent for {agent.hostname} failure alert"
                )

    @classmethod
    def handle_alert_resolve(cls, instance: Union[Agent, AutomatedTask, Check]) -> None:
        from agents.models import Agent
        from autotasks.models import AutomatedTask
        from checks.models import Check

        # set variables
        email_on_resolved = False
        text_on_resolved = False
        resolved_email_task = None
        resolved_text_task = None

        # check what the instance passed is
        if isinstance(instance, Agent):
            from agents.tasks import agent_recovery_email_task, agent_recovery_sms_task

            resolved_email_task = agent_recovery_email_task
            resolved_text_task = agent_recovery_sms_task

            alert_template = instance.alert_template
            alert = cls.objects.get(agent=instance, resolved=False)
            maintenance_mode = instance.maintenance_mode
            agent = instance

            if alert_template:
                email_on_resolved = alert_template.agent_email_on_resolved
                text_on_resolved = alert_template.agent_text_on_resolved

        elif isinstance(instance, Check):
            from checks.tasks import (
                handle_resolved_check_email_alert_task,
                handle_resolved_check_sms_alert_task,
            )

            resolved_email_task = handle_resolved_check_email_alert_task
            resolved_text_task = handle_resolved_check_sms_alert_task

            alert_template = instance.agent.alert_template
            alert = cls.objects.get(assigned_check=instance, resolved=False)
            maintenance_mode = instance.agent.maintenance_mode
            agent = instance.agent

            if alert_template:
                email_on_resolved = alert_template.check_email_on_resolved
                text_on_resolved = alert_template.check_text_on_resolved

        elif isinstance(instance, AutomatedTask):
            from autotasks.tasks import (
                handle_resolved_task_email_alert,
                handle_resolved_task_sms_alert,
            )

            resolved_email_task = handle_resolved_task_email_alert
            resolved_text_task = handle_resolved_task_sms_alert

            alert_template = instance.agent.alert_template
            alert = cls.objects.get(assigned_task=instance, resolved=False)
            maintenance_mode = instance.agent.maintenance_mode
            agent = instance.agent

            if alert_template:
                email_on_resolved = alert_template.task_email_on_resolved
                text_on_resolved = alert_template.task_text_on_resolved

        else:
            return

        # return if agent is in maintenance mode
        if maintenance_mode:
            return

        alert.resolve()

        # check if a resolved email notification should be send
        if email_on_resolved and not alert.resolved_email_sent:
            resolved_email_task.delay(pk=alert.pk)

        # check if resolved text should be sent
        if text_on_resolved and not alert.resolved_sms_sent:
            resolved_text_task.delay(pk=alert.pk)

        # check if resolved script should be run
        if (
            alert_template
            and alert_template.resolved_action
            and not alert.resolved_action_run
        ):
            r = agent.run_script(
                scriptpk=alert_template.resolved_action.pk,
                args=alert.parse_script_args(alert_template.resolved_action_args),
                timeout=alert_template.resolved_action_timeout,
                wait=True,
                full=True,
                run_on_any=True,
            )

            # command was successful
            if type(r) == dict:
                alert.resolved_action_retcode = r["retcode"]
                alert.resolved_action_stdout = r["stdout"]
                alert.resolved_action_stderr = r["stderr"]
                alert.resolved_action_execution_time = "{:.4f}".format(
                    r["execution_time"]
                )
                alert.resolved_action_run = djangotime.now()
                alert.save()
            else:
                logger.error(
                    f"Resolved action: {alert_template.action.name} failed to run on any agent for {agent.hostname} resolved alert"
                )

    def parse_script_args(self, args: list[str]):

        if not args:
            return []

        temp_args = list()
        # pattern to match for injection
        pattern = re.compile(".*\\{\\{alert\\.(.*)\\}\\}.*")

        for arg in args:
            match = pattern.match(arg)
            if match:
                name = match.group(1)

                if hasattr(self, name):
                    value = f"'{getattr(self, name)}'"
                else:
                    continue

                try:
                    temp_args.append(re.sub("\\{\\{.*\\}\\}", value, arg))  # type: ignore
                except Exception as e:
                    logger.error(e)
                    continue

            else:
                temp_args.append(arg)

        return temp_args


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
