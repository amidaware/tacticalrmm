import time
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone as djangotime
from packaging import version as pyver

from agents.models import Agent
from agents.tasks import clear_faults_task, prune_agent_history
from alerts.models import Alert
from alerts.tasks import prune_resolved_alerts
from autotasks.models import AutomatedTask, TaskResult
from checks.models import Check, CheckResult
from checks.tasks import prune_check_history
from clients.models import Client, Site
from core.utils import get_core_settings
from logs.models import PendingAction
from logs.tasks import prune_audit_log, prune_debug_log
from tacticalrmm.celery import app
from tacticalrmm.constants import (
    AGENT_DEFER,
    AGENT_STATUS_ONLINE,
    AGENT_STATUS_OVERDUE,
    RESOLVE_ALERTS_LOCK,
    SYNC_SCHED_TASK_LOCK,
    AlertSeverity,
    AlertType,
    PAAction,
    PAStatus,
    TaskStatus,
    TaskSyncStatus,
)
from tacticalrmm.helpers import rand_range
from tacticalrmm.utils import DjangoConnectionThreadPoolExecutor, redis_lock

if TYPE_CHECKING:
    from django.db.models import QuerySet


@app.task
def core_maintenance_tasks() -> None:
    AutomatedTask.objects.filter(
        remove_if_not_scheduled=True, expire_date__lt=djangotime.now()
    ).delete()

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


@app.task
def resolve_pending_actions() -> None:
    # change agent update pending status to completed if agent has just updated
    actions: "QuerySet[PendingAction]" = (
        PendingAction.objects.select_related("agent")
        .defer("agent__services", "agent__wmi_detail")
        .filter(action_type=PAAction.AGENT_UPDATE, status=PAStatus.PENDING)
    )

    to_update: list[int] = [
        action.id
        for action in actions
        if pyver.parse(action.agent.version) == pyver.parse(settings.LATEST_AGENT_VER)
        and action.agent.status == AGENT_STATUS_ONLINE
    ]

    PendingAction.objects.filter(pk__in=to_update).update(status=PAStatus.COMPLETED)


def _get_agent_qs() -> "QuerySet[Agent]":
    qs: "QuerySet[Agent]" = (
        Agent.objects.defer(*AGENT_DEFER)
        .select_related(
            "site__server_policy",
            "site__workstation_policy",
            "site__client__server_policy",
            "site__client__workstation_policy",
            "policy",
            "policy__alert_template",
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
            Prefetch(
                "taskresults",
                queryset=TaskResult.objects.select_related("task"),
            ),
            "autotasks",
        )
    )
    return qs


@app.task(bind=True)
def resolve_alerts_task(self) -> str:
    with redis_lock(RESOLVE_ALERTS_LOCK, self.app.oid) as acquired:
        if not acquired:
            return f"{self.app.oid} still running"

        # TODO rework this to not use an agent queryset, use Alerts
        for agent in _get_agent_qs():
            if (
                pyver.parse(agent.version) >= pyver.parse("1.6.0")
                and agent.status == AGENT_STATUS_ONLINE
            ):
                # handles any alerting actions
                if Alert.objects.filter(
                    alert_type=AlertType.AVAILABILITY, agent=agent, resolved=False
                ).exists():
                    Alert.handle_alert_resolve(agent)

        return "completed"


@app.task(bind=True)
def sync_scheduled_tasks(self) -> str:
    with redis_lock(SYNC_SCHED_TASK_LOCK, self.app.oid) as acquired:
        if not acquired:
            return f"{self.app.oid} still running"

        task_actions = []  # list of tuples
        for agent in _get_agent_qs():
            if (
                pyver.parse(agent.version) >= pyver.parse("1.6.0")
                and agent.status == AGENT_STATUS_ONLINE
            ):
                # create a list of tasks to be synced so we can run them in parallel later with thread pool executor
                for task in agent.get_tasks_with_policies():
                    agent_obj = agent if task.policy else None

                    # policy tasks will be an empty dict on initial
                    if (not task.task_result) or (
                        isinstance(task.task_result, TaskResult)
                        and task.task_result.sync_status == TaskSyncStatus.INITIAL
                    ):
                        task_actions.append(("create", task.id, agent_obj))
                    elif (
                        isinstance(task.task_result, TaskResult)
                        and task.task_result.sync_status
                        == TaskSyncStatus.PENDING_DELETION
                    ):
                        task_actions.append(("delete", task.id, agent_obj))
                    elif (
                        isinstance(task.task_result, TaskResult)
                        and task.task_result.sync_status == TaskSyncStatus.NOT_SYNCED
                    ):
                        task_actions.append(("modify", task.id, agent_obj))

        def _handle_task(actions: tuple[str, int, Any]) -> None:
            time.sleep(rand_range(50, 600))
            task: "AutomatedTask" = AutomatedTask.objects.get(id=actions[1])
            if actions[0] == "create":
                task.create_task_on_agent(agent=actions[2])
            elif actions[0] == "modify":
                task.modify_task_on_agent(agent=actions[2])
            elif actions[0] == "delete":
                task.delete_task_on_agent(agent=actions[2])

        # TODO this is a janky hack
        # Rework this with asyncio. Need to rewrite all sync db operations with django's new async api
        with DjangoConnectionThreadPoolExecutor(max_workers=50) as executor:
            executor.map(_handle_task, task_actions)

        return "completed"


def _get_failing_data(agents: "QuerySet[Agent]") -> dict[str, bool]:
    data = {"error": False, "warning": False}
    for agent in agents:
        if agent.maintenance_mode:
            break

        if (
            agent.overdue_email_alert
            or agent.overdue_text_alert
            or agent.overdue_dashboard_alert
        ):
            if agent.status == AGENT_STATUS_OVERDUE:
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
                    and task.task_result.status == TaskStatus.FAILING
                    and task.alert_severity == AlertSeverity.ERROR
                ):
                    data["error"] = True
                elif (
                    not data["warning"]
                    and task.task_result.status == TaskStatus.FAILING
                    and task.alert_severity == AlertSeverity.WARNING
                ):
                    data["warning"] = True

    return data


@app.task
def cache_db_fields_task() -> None:
    qs = _get_agent_qs()
    # update client/site failing check fields and agent counts
    for site in Site.objects.all():
        agents = qs.filter(site=site)
        site.failing_checks = _get_failing_data(agents)
        site.save(update_fields=["failing_checks"])

    for client in Client.objects.all():
        agents = qs.filter(site__client=client)
        client.failing_checks = _get_failing_data(agents)
        client.save(update_fields=["failing_checks"])
