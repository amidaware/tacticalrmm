from typing import Dict, Any, TYPE_CHECKING

from agents.models import Agent
from agents.tasks import clear_faults_task, prune_agent_history
from alerts.models import Alert
from alerts.tasks import prune_resolved_alerts
from autotasks.models import TaskResult
from checks.tasks import prune_check_history
from clients.models import Client, Site
from checks.models import Check, CheckResult
from core.utils import get_core_settings
from django.conf import settings
from django.db.models import Prefetch, Exists, OuterRef
from logs.models import PendingAction
from logs.tasks import prune_audit_log, prune_debug_log
from packaging import version as pyver

from tacticalrmm.celery import app
from tacticalrmm.constants import AGENT_DEFER

if TYPE_CHECKING:
    from django.db.models import QuerySet


@app.task
def core_maintenance_tasks() -> None:
    core = get_core_settings()

    # remove old CheckHistory data
    if core.check_history_prune_days > 0:
        prune_check_history.delay(core.check_history_prune_days)

    # remove old resolved alerts
    if core.resolved_alerts_prune_days > 0:
        prune_resolved_alerts.delay(core.resolved_alerts_prune_days)

    # remove old agent history
    if core.agent_history_prune_days > 0:
        prune_agent_history.delay(core.agent_history_prune_days)

    # remove old debug logs
    if core.debug_log_prune_days > 0:
        prune_debug_log.delay(core.debug_log_prune_days)

    # remove old audit logs
    if core.audit_log_prune_days > 0:
        prune_audit_log.delay(core.audit_log_prune_days)

    # clear faults
    if core.clear_faults_days > 0:
        clear_faults_task.delay(core.clear_faults_days)


def _get_failing_data(agents: "QuerySet[Any]") -> Dict[str, bool]:
    data = {"error": False, "warning": False}
    for agent in agents:
        if agent.maintenance_mode:
            break

        if (
            agent.overdue_email_alert
            or agent.overdue_text_alert
            or agent.overdue_dashboard_alert
        ):
            if agent.status == "overdue":
                data["error"] = True
                break

        if agent.checks["has_failing_checks"]:

            if agent.checks["warning"]:
                data["warning"] = True

            if agent.checks["failing"]:
                data["error"] = True
                break

        if not data["error"] and not data["warning"]:
            for task in agent.get_tasks_with_policies():
                if data["error"] and data["warning"]:
                    break
                elif not isinstance(task.task_result, TaskResult):
                    continue
                elif (
                    not data["error"]
                    and task.task_result.status == "failing"
                    and task.alert_severity == "error"
                ):
                    data["error"] = True
                elif (
                    not data["warning"]
                    and task.task_result.status == "failing"
                    and task.alert_severity == "warning"
                ):
                    data["warning"]

    return data


@app.task
def cache_db_fields_task() -> None:

    agent_queryset = (
        Agent.objects.defer(*AGENT_DEFER)
        .select_related(
            "site__server_policy",
            "site__workstation_policy",
            "site__client__server_policy",
            "site__client__workstation_policy",
            "policy",
            "alert_template",
        )
        .prefetch_related(
            Prefetch(
                "agentchecks",
                queryset=Check.objects.select_related("script"),
            ),
            Prefetch(
                "checkresults",
                queryset=CheckResult.objects.select_related("assigned_check"),
            ),
            "autotasks",
            Prefetch(
                "taskresults",
                queryset=TaskResult.objects.select_related("task"),
            ),
        )
    )
    # update client/site failing check fields and agent counts
    for site in Site.objects.all():
        agents = agent_queryset.filter(site=site)
        site.failing_checks = _get_failing_data(agents)
        site.save(update_fields=["failing_checks"])

    for client in Client.objects.all():
        agents = agent_queryset.filter(site__client=client)
        client.failing_checks = _get_failing_data(agents)
        client.save(update_fields=["failing_checks"])

    for agent in agent_queryset.annotate(
        has_pending_actions=Exists(
            PendingAction.objects.filter(
                pk=OuterRef("pk"), action_type="agent_update", status="pending"
            )
        )
    ):
        if (
            pyver.parse(agent.version) >= pyver.parse("1.6.0")
            and agent.status == "online"
        ):
            # change agent update pending status to completed if agent has just updated
            if (
                pyver.parse(agent.version) == pyver.parse(settings.LATEST_AGENT_VER)
                and agent.has_pending_actions
            ):
                agent.pendingactions.filter(
                    action_type="agent_update", status="pending"
                ).update(status="completed")

            # sync scheduled tasks
            for task in agent.get_tasks_with_policies():
                if not task.task_result or task.task_result.sync_status == "initial":
                    task.create_task_on_agent(agent=agent if task.policy else None)
                elif task.task_result.sync_status == "pendingdeletion":
                    task.delete_task_on_agent(agent=agent if task.policy else None)
                elif task.task_result.sync_status == "notsynced":
                    task.modify_task_on_agent(agent=agent if task.policy else None)
                elif task.task_result.sync_status == "synced":
                    continue

            # handles any alerting actions
            if Alert.objects.filter(
                alert_type="availability", agent=agent, resolved=False
            ).exists():
                Alert.handle_alert_resolve(agent)
