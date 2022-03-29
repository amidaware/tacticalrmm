import pytz
from agents.models import Agent
from agents.tasks import clear_faults_task, prune_agent_history
from alerts.models import Alert
from alerts.tasks import prune_resolved_alerts
from autotasks.models import AutomatedTask
from autotasks.tasks import delete_win_task_schedule
from checks.tasks import prune_check_history
from clients.models import Client, Site
from core.models import CoreSettings
from django.conf import settings
from django.utils import timezone as djangotime
from logs.tasks import prune_audit_log, prune_debug_log
from packaging import version as pyver

from tacticalrmm.celery import app
from tacticalrmm.constants import AGENT_DEFER


@app.task
def core_maintenance_tasks():
    core = CoreSettings.objects.first()

    # remove old CheckHistory data
    if core.check_history_prune_days > 0:  # type: ignore
        prune_check_history.delay(core.check_history_prune_days)  # type: ignore

    # remove old resolved alerts
    if core.resolved_alerts_prune_days > 0:  # type: ignore
        prune_resolved_alerts.delay(core.resolved_alerts_prune_days)  # type: ignore

    # remove old agent history
    if core.agent_history_prune_days > 0:  # type: ignore
        prune_agent_history.delay(core.agent_history_prune_days)  # type: ignore

    # remove old debug logs
    if core.debug_log_prune_days > 0:  # type: ignore
        prune_debug_log.delay(core.debug_log_prune_days)  # type: ignore

    # remove old audit logs
    if core.audit_log_prune_days > 0:  # type: ignore
        prune_audit_log.delay(core.audit_log_prune_days)  # type: ignore

    # clear faults
    if core.clear_faults_days > 0:  # type: ignore
        clear_faults_task.delay(core.clear_faults_days)  # type: ignore


def _get_failing_data(agents):
    data = {"error": False, "warning": False}
    for agent in agents:
        if agent.maintenance_mode:
            break

        if agent.overdue_email_alert or agent.overdue_text_alert:
            if agent.status == "overdue":
                data["error"] = True
                break

        if agent.checks["has_failing_checks"]:

            if agent.checks["warning"]:
                data["warning"] = True

            if agent.checks["failing"]:
                data["error"] = True
                break

        for task in agent.get_tasks_with_policies():
            if not task.task_result:
                continue
            elif task.task_result.status == "failing" and task.task_result.alert_severity == "error":
                data["error"] = True
                break

    return data


@app.task
def cache_db_fields_task():
    # update client/site failing check fields and agent counts
    for site in Site.objects.all():
        agents = site.agents.defer(*AGENT_DEFER)
        site.failing_checks = _get_failing_data(agents)
        site.agent_count = agents.count()
        site.save(update_fields=["failing_checks", "agent_count"])

    for client in Client.objects.all():
        agents = Agent.objects.defer(*AGENT_DEFER).filter(site__client=client)
        client.failing_checks = _get_failing_data(agents)
        client.agent_count = agents.count()
        client.save(update_fields=["failing_checks", "agent_count"])

    for agent in Agent.objects.defer(*AGENT_DEFER):
        if (
            pyver.parse(agent.version) >= pyver.parse("1.6.0")
            and agent.status == "online"
        ):
            # change agent update pending status to completed if agent has just updated
            if (
                pyver.parse(agent.version) == pyver.parse(settings.LATEST_AGENT_VER)
                and agent.pendingactions.filter(
                    action_type="agentupdate", status="pending"
                ).exists()
            ):
                agent.pendingactions.filter(
                    action_type="agentupdate", status="pending"
                ).update(status="completed")

            # sync scheduled tasks
            for task in agent.get_tasks_with_policies(exclude_synced=True):
                try:
                    if not task.task_result or task.task_result.sync_status == "initial":
                        task.create_task_on_agent(agent=agent if task.policy else None)
                    if task.task_result.sync_status == "pendingdeletion":
                        task.delete_task_on_agent(agent=agent if task.policy else None)
                    elif task.task_result.sync_status == "notsynced":
                        task.modify_task_on_agent(agent=agent if task.policy else None)

                except:
                    continue

            # handles any alerting actions
            if Alert.objects.filter(agent=agent, resolved=False).exists():
                try:
                    Alert.handle_alert_resolve(agent)
                except:
                    continue

        # update pending patches and pending action counts
        agent.pending_actions_count = agent.pendingactions.filter(
            status="pending"
        ).count()
        agent.has_patches_pending = (
            agent.winupdates.filter(action="approve").filter(installed=False).exists()
        )
        agent.save(update_fields=["pending_actions_count", "has_patches_pending"])
