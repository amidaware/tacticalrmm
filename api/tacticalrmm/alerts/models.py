from __future__ import annotations

import re
from typing import TYPE_CHECKING, Union, Optional, Dict, Any, List, cast

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.fields import BooleanField, PositiveIntegerField
from django.utils import timezone as djangotime
from logs.models import BaseAuditModel, DebugLog

from tacticalrmm.models import PermissionQuerySet

if TYPE_CHECKING:
    from agents.models import Agent
    from autotasks.models import AutomatedTask, TaskResult
    from checks.models import Check, CheckResult
    from clients.models import Client, Site


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
    objects = PermissionQuerySet.as_manager()

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

    def __str__(self) -> str:
        return self.message

    @property
    def assigned_agent(self) -> "Agent":
        return self.agent

    @property
    def site(self) -> "Site":
        return self.agent.site

    @property
    def client(self) -> "Client":
        return self.agent.client

    def resolve(self) -> None:
        self.resolved = True
        self.resolved_on = djangotime.now()
        self.snoozed = False
        self.snooze_until = None
        self.save(update_fields=["resolved", "resolved_on", "snoozed", "snooze_until"])

    @classmethod
    def create_or_return_availability_alert(
        cls, agent: Agent, skip_create: bool = False
    ) -> Optional[Alert]:
        if not cls.objects.filter(agent=agent, resolved=False).exists():
            if skip_create:
                return None

            return cast(
                Alert,
                cls.objects.create(
                    agent=agent,
                    alert_type="availability",
                    severity="error",
                    message=f"{agent.hostname} in {agent.client.name}\\{agent.site.name} is overdue.",
                    hidden=True,
                ),
            )
        else:
            try:
                return cast(
                    Alert,
                    cls.objects.get(
                        agent=agent, alert_type="availability", resolved=False
                    ),
                )
            except cls.MultipleObjectsReturned:
                alerts = cls.objects.filter(
                    agent=agent, alert_type="availability", resolved=False
                )

                last_alert = cast(Alert, alerts.last())

                # cycle through other alerts and resolve
                for alert in alerts:
                    if alert.id != last_alert.pk:
                        alert.resolve()

                return last_alert
            except cls.DoesNotExist:
                return None

    @classmethod
    def create_or_return_check_alert(
        cls,
        check: "Check",
        agent: "Agent",
        alert_severity: Optional[str] = None,
        skip_create: bool = False,
    ) -> "Optional[Alert]":

        # need to pass agent if the check is a policy
        if not cls.objects.filter(
            assigned_check=check,
            agent=agent,
            resolved=False,
        ).exists():
            if skip_create:
                return None

            return cast(
                Alert,
                cls.objects.create(
                    assigned_check=check,
                    agent=agent,
                    alert_type="check",
                    severity=check.alert_severity
                    if check.check_type
                    not in ["memory", "cpuload", "diskspace", "script"]
                    else alert_severity,
                    message=f"{agent.hostname} has a {check.check_type} check: {check.readable_desc} that failed.",
                    hidden=True,
                ),
            )
        else:
            try:
                return cast(
                    Alert,
                    cls.objects.get(
                        assigned_check=check,
                        agent=agent,
                        resolved=False,
                    ),
                )
            except cls.MultipleObjectsReturned:
                alerts = cls.objects.filter(
                    assigned_check=check,
                    agent=agent,
                    resolved=False,
                )
                last_alert = cast(Alert, alerts.last())

                # cycle through other alerts and resolve
                for alert in alerts:
                    if alert.id != last_alert.pk:
                        alert.resolve()

                return last_alert
            except cls.DoesNotExist:
                return None

    @classmethod
    def create_or_return_task_alert(
        cls,
        task: "AutomatedTask",
        agent: "Agent",
        skip_create: bool = False,
    ) -> "Optional[Alert]":

        if not cls.objects.filter(
            assigned_task=task,
            agent=agent,
            resolved=False,
        ).exists():
            if skip_create:
                return None

            return cast(
                Alert,
                cls.objects.create(
                    assigned_task=task,
                    agent=agent,
                    alert_type="task",
                    severity=task.alert_severity,
                    message=f"{agent.hostname} has task: {task.name} that failed.",
                    hidden=True,
                ),
            )

        else:
            try:
                return cast(
                    Alert,
                    cls.objects.get(
                        assigned_task=task,
                        agent=agent,
                        resolved=False,
                    ),
                )
            except cls.MultipleObjectsReturned:
                alerts = cls.objects.filter(
                    assigned_task=task,
                    agent=agent,
                    resolved=False,
                )
                last_alert = cast(Alert, alerts.last())

                # cycle through other alerts and resolve
                for alert in alerts:
                    if alert.id != last_alert.pk:
                        alert.resolve()

                return last_alert
            except cls.DoesNotExist:
                return None

    @classmethod
    def handle_alert_failure(
        cls, instance: Union[Agent, TaskResult, CheckResult]
    ) -> None:
        from agents.models import Agent
        from autotasks.models import TaskResult
        from checks.models import CheckResult

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
        run_script_action = None

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
                run_script_action = alert_template.agent_script_actions

        elif isinstance(instance, CheckResult):
            from checks.tasks import (
                handle_check_email_alert_task,
                handle_check_sms_alert_task,
            )

            email_task = handle_check_email_alert_task
            text_task = handle_check_sms_alert_task

            email_alert = instance.assigned_check.email_alert
            text_alert = instance.assigned_check.text_alert
            dashboard_alert = instance.assigned_check.dashboard_alert
            alert_template = instance.agent.alert_template
            maintenance_mode = instance.agent.maintenance_mode
            alert_severity = (
                instance.assigned_check.alert_severity
                if instance.assigned_check.check_type
                not in ["memory", "cpuload", "diskspace", "script"]
                else instance.alert_severity
            )
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
                run_script_action = alert_template.check_script_actions

        elif isinstance(instance, TaskResult):
            from autotasks.tasks import handle_task_email_alert, handle_task_sms_alert

            email_task = handle_task_email_alert
            text_task = handle_task_sms_alert

            email_alert = instance.task.email_alert
            text_alert = instance.task.text_alert
            dashboard_alert = instance.task.dashboard_alert
            alert_template = instance.agent.alert_template
            maintenance_mode = instance.agent.maintenance_mode
            alert_severity = instance.task.alert_severity
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
                run_script_action = alert_template.task_script_actions

        else:
            return

        alert = instance.get_or_create_alert_if_needed(alert_template)

        # return if agent is in maintenance mode
        if not alert or maintenance_mode:
            return

        # check if alert severity changed and update the alert
        if alert_severity != alert.severity:
            alert.severity = alert_severity
            alert.save(update_fields=["severity"])

        # create alert in dashboard if enabled
        if dashboard_alert or always_dashboard:

            # check if alert template is set and specific severities are configured
            if (
                not alert_template
                or alert_template
                and dashboard_severities
                and alert.severity in dashboard_severities
            ):
                alert.hidden = False
                alert.save(update_fields=["hidden"])

        # send email if enabled
        if email_alert or always_email:

            # check if alert template is set and specific severities are configured
            if (
                not alert_template
                or alert_template
                and email_severities
                and alert.severity in email_severities
            ):
                email_task.delay(
                    pk=alert.pk,
                    alert_interval=alert_interval,
                )

        # send text if enabled
        if text_alert or always_text:

            # check if alert template is set and specific severities are configured
            if (
                not alert_template
                or alert_template
                and text_severities
                and alert.severity in text_severities
            ):
                text_task.delay(pk=alert.pk, alert_interval=alert_interval)

        # check if any scripts should be run
        if (
            alert_template
            and alert_template.action
            and run_script_action
            and not alert.action_run
        ):
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
                DebugLog.error(
                    agent=agent,
                    log_type="scripting",
                    message=f"Failure action: {alert_template.action.name} failed to run on any agent for {agent.hostname}({agent.pk}) failure alert",
                )

    @classmethod
    def handle_alert_resolve(
        cls, instance: Union[Agent, TaskResult, CheckResult]
    ) -> None:
        from agents.models import Agent
        from autotasks.models import TaskResult
        from checks.models import CheckResult

        # set variables
        email_on_resolved = False
        text_on_resolved = False
        resolved_email_task = None
        resolved_text_task = None
        run_script_action = None

        # check what the instance passed is
        if isinstance(instance, Agent):
            from agents.tasks import agent_recovery_email_task, agent_recovery_sms_task

            resolved_email_task = agent_recovery_email_task
            resolved_text_task = agent_recovery_sms_task

            alert_template = instance.alert_template
            maintenance_mode = instance.maintenance_mode
            agent = instance

            if alert_template:
                email_on_resolved = alert_template.agent_email_on_resolved
                text_on_resolved = alert_template.agent_text_on_resolved
                run_script_action = alert_template.agent_script_actions

        elif isinstance(instance, CheckResult):
            from checks.tasks import (
                handle_resolved_check_email_alert_task,
                handle_resolved_check_sms_alert_task,
            )

            resolved_email_task = handle_resolved_check_email_alert_task
            resolved_text_task = handle_resolved_check_sms_alert_task

            alert_template = instance.agent.alert_template
            maintenance_mode = instance.agent.maintenance_mode
            agent = instance.agent

            if alert_template:
                email_on_resolved = alert_template.check_email_on_resolved
                text_on_resolved = alert_template.check_text_on_resolved
                run_script_action = alert_template.check_script_actions

        elif isinstance(instance, TaskResult):
            from autotasks.tasks import (
                handle_resolved_task_email_alert,
                handle_resolved_task_sms_alert,
            )

            resolved_email_task = handle_resolved_task_email_alert
            resolved_text_task = handle_resolved_task_sms_alert

            alert_template = instance.agent.alert_template
            maintenance_mode = instance.agent.maintenance_mode
            agent = instance.agent

            if alert_template:
                email_on_resolved = alert_template.task_email_on_resolved
                text_on_resolved = alert_template.task_text_on_resolved
                run_script_action = alert_template.task_script_actions

        else:
            return

        alert = instance.get_or_create_alert_if_needed(alert_template)

        # return if agent is in maintenance mode
        if not alert or maintenance_mode:
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
            and run_script_action
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
                DebugLog.error(
                    agent=agent,
                    log_type="scripting",
                    message=f"Resolved action: {alert_template.action.name} failed to run on any agent for {agent.hostname}({agent.pk}) resolved alert",
                )

    def parse_script_args(self, args: List[str]) -> List[str]:

        if not args:
            return []

        temp_args = list()
        # pattern to match for injection
        pattern = re.compile(".*\\{\\{alert\\.(.*)\\}\\}.*")

        for arg in args:
            match = pattern.match(arg)
            if match:
                name = match.group(1)

                # check if attr exists and isn't a function
                if hasattr(self, name) and not callable(getattr(self, name)):
                    value = f"'{getattr(self, name)}'"
                else:
                    continue

                try:
                    temp_args.append(re.sub("\\{\\{.*\\}\\}", value, arg))
                except Exception as e:
                    DebugLog.error(log_type="scripting", message=str(e))
                    continue

            else:
                temp_args.append(arg)

        return temp_args


class AlertTemplate(BaseAuditModel):
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
    agent_script_actions = BooleanField(null=True, blank=True, default=True)

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
    check_script_actions = BooleanField(null=True, blank=True, default=True)

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
    task_script_actions = BooleanField(null=True, blank=True, default=True)

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

    def __str__(self) -> str:
        return self.name

    def is_agent_excluded(self, agent: "Agent") -> bool:
        return (
            agent in self.excluded_agents.all()
            or agent.site in self.excluded_sites.all()
            or agent.client in self.excluded_clients.all()
            or agent.monitoring_type == "workstation"
            and self.exclude_workstations
            or agent.monitoring_type == "server"
            and self.exclude_servers
        )

    @staticmethod
    def serialize(alert_template: AlertTemplate) -> Dict[str, Any]:
        # serializes the agent and returns json
        from .serializers import AlertTemplateAuditSerializer

        return AlertTemplateAuditSerializer(alert_template).data

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
