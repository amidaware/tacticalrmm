import asyncio
import traceback
from contextlib import suppress
from time import sleep
from typing import TYPE_CHECKING, Any

import nats
from django.conf import settings
from redis import from_url
from django.core.cache import cache
from django.db import transaction
from django.db.models import Prefetch
from django.db.utils import DatabaseError
from django.utils import timezone as djangotime
from packaging import version as pyver

from accounts.models import User
from accounts.utils import is_superuser
from agents.models import Agent
from agents.tasks import clear_faults_task, prune_agent_history
from agents.utils import calculate_agent_checks
from alerts.models import Alert
from alerts.tasks import prune_resolved_alerts
from autotasks.models import AutomatedTask, TaskResult
from checks.models import Check, CheckHistory, CheckResult
from checks.tasks import prune_check_history
from clients.models import Client, Site
from core.mesh_utils import (
    MeshSync,
    build_mesh_display_name,
    has_mesh_perms,
    transform_mesh,
    transform_trmm,
)
from core.models import CoreSettings
from core.utils import get_core_settings, get_mesh_ws_url, make_alpha_numeric
from ee.reporting.tasks import prune_report_history_task
from logs.models import PendingAction
from logs.tasks import prune_audit_log, prune_debug_log
from tacticalrmm.celery import app
from tacticalrmm.constants import (
    AGENT_CHECKS_CACHE_PREFIX,
    AGENT_DEFER,
    AGENT_STATUS_ONLINE,
    AGENT_STATUS_OVERDUE,
    CACHE_DB_FIELDS_TASK_LOCK,
    RESOLVE_ALERTS_LOCK,
    SYNC_MESH_PERMS_TASK_LOCK,
    SYNC_SCHED_TASK_LOCK,
    AgentPlat,
    AlertSeverity,
    AlertType,
    PAAction,
    PAStatus,
    TaskRunStatus,
    TaskStatus,
    TaskSyncStatus,
    TaskType,
)
from tacticalrmm.helpers import make_random_password, setup_nats_options
from tacticalrmm.logger import logger
from tacticalrmm.nats_utils import a_nats_cmd, abulk_nats_command
from tacticalrmm.permissions import _has_perm_on_agent
from tacticalrmm.scheduler import (
    should_run_daily_task,
    should_run_monthly_dow_task,
    should_run_monthly_task,
    should_run_once_task,
    should_run_weekly_task,
)
from tacticalrmm.utils import redis_lock

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from nats.aio.client import Client as NATSClient


def remove_orphaned_history_results() -> int:
    try:
        with transaction.atomic():
            check_hist_agentids = CheckHistory.objects.values_list(
                "agent_id", flat=True
            ).distinct()
            current_agentids = set(Agent.objects.values_list("agent_id", flat=True))
            orphaned_agentids = [
                i for i in check_hist_agentids if i not in current_agentids
            ]
            count, _ = CheckHistory.objects.filter(
                agent_id__in=orphaned_agentids
            ).delete()
            return count
    except Exception as e:
        logger.error(str(e))
        return 0


@app.task
def core_maintenance_tasks() -> None:
    AutomatedTask.objects.filter(
        remove_if_not_scheduled=True, expire_date__lt=djangotime.now()
    ).delete()

    remove_orphaned_history_results()

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

    if core.report_history_prune_days > 0:
        prune_report_history_task.delay(core.report_history_prune_days)


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

        actions: list[tuple[str, int, Agent, Any, str, str]] = []  # list of tuples

        for agent in _get_agent_qs():
            if agent.is_posix:
                for task in agent.get_tasks_with_policies():
                    try:
                        _ = TaskResult.objects.get(agent=agent, task=task)
                    except TaskResult.DoesNotExist:
                        TaskResult.objects.create(
                            agent=agent, task=task, sync_status=TaskSyncStatus.SYNCED
                        )

            elif (
                pyver.parse(agent.version) >= pyver.parse("1.6.0")
                and agent.status == AGENT_STATUS_ONLINE
            ):
                # create a list of tasks to be synced so we can run them asynchronously
                for task in agent.get_tasks_with_policies():
                    # TODO can we just use agent??
                    agent_obj: "Agent" = agent if task.policy else task.agent

                    # onboarding tasks require agent >= 2.6.0
                    if task.task_type == TaskType.ONBOARDING and pyver.parse(
                        agent.version
                    ) < pyver.parse("2.6.0"):
                        continue

                    # policy tasks will be an empty dict on initial
                    if (not task.task_result) or (
                        isinstance(task.task_result, TaskResult)
                        and task.task_result.sync_status == TaskSyncStatus.INITIAL
                    ):
                        actions.append(
                            (
                                "create",
                                task.id,
                                agent_obj,
                                task.generate_nats_task_payload(),
                                agent.agent_id,
                                agent.hostname,
                            )
                        )
                    elif (
                        isinstance(task.task_result, TaskResult)
                        and task.task_result.sync_status
                        == TaskSyncStatus.PENDING_DELETION
                    ):
                        actions.append(
                            (
                                "delete",
                                task.id,
                                agent_obj,
                                {},
                                agent.agent_id,
                                agent.hostname,
                            )
                        )
                    elif (
                        isinstance(task.task_result, TaskResult)
                        and task.task_result.sync_status == TaskSyncStatus.NOT_SYNCED
                    ):
                        actions.append(
                            (
                                "modify",
                                task.id,
                                agent_obj,
                                task.generate_nats_task_payload(),
                                agent.agent_id,
                                agent.hostname,
                            )
                        )

        async def _handle_task_on_agent(
            nc: "NATSClient", actions: tuple[str, int, Agent, Any, str, str]
        ) -> None:
            # tuple: (0: action, 1: task.id, 2: agent object, 3: nats task payload, 4: agent_id, 5: agent hostname)
            action = actions[0]
            task_id = actions[1]
            agent = actions[2]
            payload = actions[3]
            agent_id = actions[4]
            hostname = actions[5]

            task: "AutomatedTask" = await AutomatedTask.objects.aget(id=task_id)
            try:
                task_result = await TaskResult.objects.aget(agent=agent, task=task)
            except TaskResult.DoesNotExist:
                task_result = await TaskResult.objects.acreate(agent=agent, task=task)

            if action in ("create", "modify"):
                logger.debug(payload)
                nats_data = {
                    "func": "schedtask",
                    "schedtaskpayload": payload,
                }

                r = await a_nats_cmd(nc=nc, sub=agent_id, data=nats_data, timeout=10)
                if r != "ok":
                    if action == "create":
                        task_result.sync_status = TaskSyncStatus.INITIAL
                    else:
                        task_result.sync_status = TaskSyncStatus.NOT_SYNCED

                    logger.error(
                        f"Unable to {action} scheduled task {task.name} on {hostname}: {r}"
                    )
                else:
                    task_result.sync_status = TaskSyncStatus.SYNCED
                    logger.info(
                        f"{hostname} task {task.name} was {'created' if action == 'create' else 'modified'}"
                    )

                await task_result.asave(update_fields=["sync_status"])
            # delete
            else:
                nats_data = {
                    "func": "delschedtask",
                    "schedtaskpayload": {"name": task.win_task_name},
                }
                r = await a_nats_cmd(nc=nc, sub=agent_id, data=nats_data, timeout=10)

                if r != "ok" and "The system cannot find the file specified" not in r:
                    task_result.sync_status = TaskSyncStatus.PENDING_DELETION

                    with suppress(DatabaseError):
                        await task_result.asave(update_fields=["sync_status"])

                    logger.error(
                        f"Unable to {action} scheduled task {task.name} on {hostname}: {r}"
                    )
                else:
                    task_name = task.name
                    await task.adelete()
                    logger.info(f"{hostname} task {task_name} was deleted.")

        async def _run():
            opts = setup_nats_options()
            try:
                nc = await nats.connect(**opts)
            except Exception as e:
                ret = str(e)
                logger.error(ret)
                return ret

            if tasks := [_handle_task_on_agent(nc, task) for task in actions]:
                await asyncio.gather(*tasks)

            await nc.flush()
            await nc.close()

        asyncio.run(_run())
        return "ok"


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


@app.task(bind=True)
def cache_db_fields_task(self) -> None | str:
    with redis_lock(CACHE_DB_FIELDS_TASK_LOCK, self.app.oid) as acquired:
        if not acquired:
            return f"{self.app.oid} still running"

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

        for agent in qs.iterator(chunk_size=100):
            data = calculate_agent_checks(agent)
            cache.set(f"{AGENT_CHECKS_CACHE_PREFIX}{agent.pk}", data, 86400)


@app.task(bind=True)
def sync_mesh_perms_task(self):

    if getattr(settings, "TRMM_DISABLE_MESH_SYNC_TASK", False):
        return

    with redis_lock(SYNC_MESH_PERMS_TASK_LOCK, self.app.oid) as acquired:
        if not acquired:
            return f"{self.app.oid} still running"

        try:
            core = CoreSettings.objects.first()
            do_not_sync = not core.sync_mesh_with_trmm
            uri = get_mesh_ws_url()
            ms = MeshSync(uri)

            if do_not_sync:
                for user in ms.mesh_users:
                    ms.delete_user_from_mesh(mesh_user_id=user)

                return

            company_name = core.mesh_company_name
            mnp = {"action": "nodes"}
            mesh_nodes_raw = ms.mesh_action(payload=mnp, wait=True)["nodes"]

            users = User.objects.select_related("role").filter(
                agent=None,
                is_installer_user=False,
                is_active=True,
                block_dashboard_login=False,
            )

            trmm_agents_meshnodeids = [
                f"node//{i.hex_mesh_node_id}"
                for i in Agent.objects.only("mesh_node_id")
                if i.mesh_node_id and i.hex_mesh_node_id != "error"
            ]

            mesh_users_dict = {}
            for user in users:
                full_name = build_mesh_display_name(
                    first_name=user.first_name,
                    last_name=user.last_name,
                    company_name=company_name,
                )

                # mesh user creation will fail if same email exists for another user
                # make sure that doesn't happen by making a random email
                rand_str1 = make_random_password(len=6)
                rand_str2 = make_random_password(len=5)
                # for trmm users whos usernames are emails
                email_prefix = make_alpha_numeric(user.username)
                email = f"{email_prefix}.{rand_str1}@tacticalrmm-do-not-change-{rand_str2}.local"
                mesh_users_dict[user.mesh_user_id] = {
                    "_id": user.mesh_user_id,
                    "username": user.mesh_username,
                    "full_name": full_name,
                    "email": email,
                }

            new_trmm_agents = []
            for agent in Agent.objects.defer(*AGENT_DEFER):
                if not agent.mesh_node_id:
                    continue
                agent_dict = {
                    "node_id": f"node//{agent.hex_mesh_node_id}",
                    "hostname": agent.hostname,
                }
                tmp: list[dict[str, str]] = []
                for user in users:
                    if not has_mesh_perms(user=user):
                        logger.debug(f"No mesh perms for {user} on {agent.hostname}")
                        continue

                    if (user.is_superuser or is_superuser(user)) or _has_perm_on_agent(
                        user, agent.agent_id
                    ):
                        tmp.append({"_id": user.mesh_user_id})

                agent_dict["links"] = tmp
                new_trmm_agents.append(agent_dict)

            final_trmm = transform_trmm(new_trmm_agents)
            final_mesh = transform_mesh(mesh_nodes_raw)

            # delete users first
            source_users_global = set()
            for item in final_trmm:
                source_users_global.update(item["user_ids"])

            target_users_global = set()
            for item in final_mesh:
                target_users_global.update(item["user_ids"])

            # identify and create new users
            new_users = list(source_users_global - target_users_global)
            for user_id in new_users:
                user_info = mesh_users_dict[user_id]
                logger.info(f"Adding new user {user_info['username']} to mesh")
                ms.add_user_to_mesh(user_info=user_info)

            users_to_delete_globally = list(target_users_global - source_users_global)
            for user_id in users_to_delete_globally:
                logger.info(f"Deleting {user_id} from mesh")
                ms.delete_user_from_mesh(mesh_user_id=user_id)

            source_map = {item["node_id"]: set(item["user_ids"]) for item in final_trmm}
            target_map = {item["node_id"]: set(item["user_ids"]) for item in final_mesh}

            def _get_sleep_after_n_inter(n):
                # {number of agents: chunk size}
                thresholds = {250: 150, 500: 275, 800: 300, 1000: 340}
                for threshold, value in sorted(thresholds.items()):
                    if n <= threshold:
                        return value

                return 375

            iter_count = 0
            sleep_after = _get_sleep_after_n_inter(len(source_map))

            for node_id, source_users in source_map.items():
                # skip agents without valid node id
                if node_id not in trmm_agents_meshnodeids:
                    continue

                target_users = target_map.get(node_id, set()) - set(
                    users_to_delete_globally
                )
                source_users_adjusted = source_users - set(users_to_delete_globally)

                # find users that need to be added or deleted
                users_to_add = list(source_users_adjusted - target_users)
                users_to_delete = list(target_users - source_users_adjusted)

                if users_to_add or users_to_delete:
                    iter_count += 1

                if users_to_add:
                    logger.info(f"Adding {users_to_add} to {node_id}")
                    ms.add_users_to_node(node_id=node_id, user_ids=users_to_add)

                if users_to_delete:
                    logger.info(f"Deleting {users_to_delete} from {node_id}")
                    ms.delete_users_from_node(node_id=node_id, user_ids=users_to_delete)

                if iter_count % sleep_after == 0 and iter_count != 0:
                    # mesh is very inefficient with sql, give it time to catch up so we don't crash the system
                    logger.info(
                        f"Sleeping for 7 seconds after {iter_count} iterations."
                    )
                    sleep(7)

            # after all done, see if need to update display name
            ms2 = MeshSync(uri)
            unique_ids = ms2.get_unique_mesh_users(new_trmm_agents)
            for user in unique_ids:
                try:
                    mesh_realname = ms2.mesh_users[user]["realname"]
                except KeyError:
                    mesh_realname = ""
                trmm_realname = mesh_users_dict[user]["full_name"]
                if mesh_realname != trmm_realname:
                    logger.info(
                        f"Display names don't match. Updating {user} name from {mesh_realname} to {trmm_realname}"
                    )
                    ms2.update_mesh_displayname(user_info=mesh_users_dict[user])

        except Exception:
            logger.debug(traceback.format_exc())


@app.task
def scheduled_task_runner():
    now = djangotime.now()

    task_results = (
        TaskResult.objects.filter(task__enabled=True)
        .select_related("task", "agent")
        .only(
            "last_run",
            "run_status",
            "locked_at",
            "agent__time_zone",
            "agent__agent_id",
            "agent__hostname",
            "agent__plat",
            "task__name",
            "task__enabled",
            "task__task_type",
            "task__run_time_date",
            "task__run_time_bit_weekdays",
            "task__monthly_days_of_month",
            "task__monthly_months_of_year",
            "task__monthly_weeks_of_month",
        )
        .exclude(agent__plat=AgentPlat.WINDOWS)
    )

    items = []
    task_result_pks = []
    payload = {"func": "runtask"}

    for task_result in task_results:
        task = task_result.task
        agent = task_result.agent
        run = False

        if (
            task_result.locked_at
            and task_result.locked_at > now - djangotime.timedelta(seconds=55)
        ):
            # prevent race
            logger.error(
                f"Task {task.name} on {agent.hostname} already executed too recently, skipping."
            )
            continue

        if task.task_type == TaskType.DAILY:
            run = should_run_daily_task(task, agent, now)

        elif task.task_type == TaskType.WEEKLY:
            run = should_run_weekly_task(task, agent, now)

        elif task.task_type == TaskType.MONTHLY:
            run = should_run_monthly_task(task, agent, now)

        elif task.task_type == TaskType.MONTHLY_DOW:
            run = should_run_monthly_dow_task(task, agent, now)

        elif task.task_type == TaskType.RUN_ONCE:
            if not task_result.last_run:
                run = should_run_once_task(task, agent, now)

        elif task.task_type == TaskType.ONBOARDING:
            if not task_result.last_run and task_result.run_status not in {
                TaskRunStatus.RUNNING,
                TaskRunStatus.COMPLETED,
            }:
                run = True

        if run:
            tmp = {**payload}
            tmp["taskpk"] = task.pk
            items.append((agent.agent_id, tmp))
            task_result_pks.append(task_result.pk)
            logger.debug(
                f"Running {task.task_type} task {task.name} on {agent.hostname}"
            )

    if items:
        with transaction.atomic():
            updated = TaskResult.objects.filter(pk__in=task_result_pks).update(
                run_status=TaskRunStatus.RUNNING, locked_at=now
            )
            if updated:
                asyncio.run(abulk_nats_command(items=items))
                logger.debug(items)

    return items


@app.task
def dispatch_due_ai_tasks():
    """Poller (runs every minute via celerybeat): queue any scheduled Pi AI
    tasks that are due."""
    from core.models import AITask, CoreSettings

    core = CoreSettings.objects.first()
    if not core or not core.ai_module_enabled:
        return "ai module disabled"

    now = djangotime.now()
    for task in AITask.objects.filter(enabled=True).select_related("agent"):
        due = False
        if task.schedule_type == AITask.SCHEDULE_ONCE:
            # legacy one-time: fires at its computed run_at
            if task.run_at and now >= task.run_at:
                due = True
        elif task.run_mode == "now":
            # on-demand one-shot; never auto-fired
            continue
        else:
            # recurring (interval/daily/weekly/monthly) via next_run
            if task.next_run is None:
                task.next_run = _compute_task_next_run(task)
                task.save(update_fields=["next_run"])
                continue
            if now >= task.next_run:
                due = True
        if due:
            run_ai_task.delay(task.pk)
    return "ok"


def _recover_ai_run_from_redis(run_id):
    """Read the bridge's live progress for a run from redis. Used to recover a
    result when the HTTP call to the bridge times out but the run finished."""
    import json as _json

    from redis import from_url

    try:
        with from_url(
            f"redis://{settings.REDIS_HOST}:6379", decode_responses=True
        ) as conn:
            raw = conn.get(f"pi_run:{run_id}")
        if not raw:
            return None
        live = _json.loads(raw)
    except Exception:
        return None

    lines = []
    for ev in live.get("events", []):
        t = ev.get("type")
        if t == "tool_start":
            lines.append(f"\u00bb {ev.get('tool')}({ev.get('args', '')})")
        elif t == "tool_end":
            lines.append(f"  {ev.get('result', '')}")
        elif t == "text":
            lines.append(ev.get("text", ""))
    return {
        "status": live.get("status"),
        "summary": live.get("summary", ""),
        "transcript": "\n".join(lines)[:50000],
    }


def _resolve_ai_model(model):
    """Return the given model if usable, else the global default, else None."""
    from core.models import AIModel

    if model and model.enabled and model.provider.enabled:
        return model
    return (
        AIModel.objects.filter(enabled=True, provider__enabled=True, is_default=True)
        .select_related("provider")
        .first()
    )


def _run_prompt_on_agent(*, agent, model, prompt, allow_mutating, run_id):
    """Execute one headless AI run on an agent via the bridge. Returns
    (status, summary, output)."""
    import requests as _requests

    device_facts = {
        "agent_id": agent.agent_id,
        "hostname": agent.hostname,
        "client": agent.client.name,
        "site": agent.site.name,
        "operating_system": agent.operating_system,
        "plat": agent.plat,
        "goarch": agent.goarch,
        "public_ip": agent.public_ip,
        "logged_in_username": agent.logged_in_username,
        "last_logged_in_user": agent.last_logged_in_user,
        "description": agent.description,
        "agent_version": agent.version,
        "device_url": (f"{settings.CORS_ORIGIN_WHITELIST[0]}/agents/{agent.agent_id}" if getattr(settings, "CORS_ORIGIN_WHITELIST", None) else ""),
    }
    payload = {
        "agent_id": agent.agent_id,
        "device_facts": device_facts,
        "provider": model.provider.name,
        "model_id": model.model_id,
        "api_key": model.provider.api_key,
        "thinking_level": model.thinking_level,
        "prompt": prompt,
        "allow_mutating": allow_mutating,
        "run_id": run_id,
        "helpdesk_prompt": get_core_settings().ai_helpdesk_prompt or "",
        "helpdesk_api": {
            "base_url": get_core_settings().ai_helpdesk_api_base_url or "",
            "api_key": get_core_settings().ai_helpdesk_api_key or "",
        },
        "helpdesk_code": get_core_settings().ai_helpdesk_code or "",
    }
    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    run_timeout = getattr(settings, "PI_RUN_TIMEOUT", 3600)
    try:
        r = _requests.post(f"{bridge}/pi/run", json=payload, timeout=(10, run_timeout))
        data = r.json()
        return (
            data.get("status", "error"),
            data.get("summary", ""),
            data.get("transcript", ""),
        )
    except _requests.exceptions.Timeout:
        recovered = _recover_ai_run_from_redis(run_id)
        if recovered and recovered.get("status") not in (None, "running"):
            return (
                recovered["status"],
                recovered.get("summary") or "(recovered after HTTP timeout)",
                recovered.get("transcript") or "",
            )
        return (
            "error",
            f"Run exceeded PI_RUN_TIMEOUT ({run_timeout}s) and did not finish.",
            "",
        )
    except Exception as e:
        return ("error", f"Bridge error: {e}", "")


def _run_report_on_bridge(*, model, prompt, run_id):
    """Run the end-of-batch combined-report session on the bridge (/pi/report).
    No device; the model compiles ONE report from the provided results via the
    helpdesk API. Returns (status, summary, output)."""
    import requests as _requests

    core = get_core_settings()
    payload = {
        "provider": model.provider.name,
        "model_id": model.model_id,
        "api_key": model.provider.api_key,
        "thinking_level": model.thinking_level,
        "prompt": prompt,
        "run_id": run_id,
        "helpdesk_prompt": core.ai_helpdesk_prompt or "",
        "helpdesk_api": {
            "base_url": core.ai_helpdesk_api_base_url or "",
            "api_key": core.ai_helpdesk_api_key or "",
        },
        "helpdesk_code": core.ai_helpdesk_code or "",
    }
    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    run_timeout = getattr(settings, "PI_RUN_TIMEOUT", 3600)
    try:
        r = _requests.post(f"{bridge}/pi/report", json=payload, timeout=(10, run_timeout))
        data = r.json()
        return (data.get("status", "error"), data.get("summary", ""), data.get("transcript", ""))
    except Exception as e:
        return ("error", f"Report bridge call failed: {e}", "")


@app.task
def finalize_bulk_report(agent_results, cmd_id, batch_id):
    """Chord callback: after every per-machine run of a batch finishes, compile
    ONE combined report (given all machine results) if the command defines a
    report_prompt. agent_results is the list of per-agent task returns (unused;
    the source of truth is the AITaskRun rows for this batch)."""
    import uuid

    from core.models import BulkAICommand, AITaskRun

    try:
        cmd = BulkAICommand.objects.select_related("model").get(pk=cmd_id)
    except BulkAICommand.DoesNotExist:
        return "not found"
    if not (cmd.report_prompt or "").strip():
        return "no report configured"
    if ai_killed():
        return "skipped (stopped)"

    runs = list(
        AITaskRun.objects.filter(bulk=cmd, batch_id=batch_id, agent__isnull=False)
        .select_related("agent", "agent__site__client")
    )
    if not runs:
        return "no runs"

    lines = []
    for r in runs:
        a = r.agent
        host = a.hostname if a else "?"
        try:
            client = a.client.name if a else ""
        except Exception:
            client = ""
        lines.append(
            f"- {host} | client={client} | status={r.status} | {(r.summary or '').strip()[:400]}"
        )
    digest = "\n".join(lines)

    model = _resolve_ai_model(cmd.model)
    if not model:
        return "no model"

    run_id = uuid.uuid4().hex
    run = AITaskRun.objects.create(
        bulk=cmd, agent=None, run_id=run_id, batch_id=batch_id,
        triggered_by="report", status="running",
    )
    prompt = (
        cmd.report_prompt
        + f"\n\nPER-MACHINE RESULTS ({len(runs)} machines checked in this batch):\n"
        + digest
    )
    status, summary, output = _run_report_on_bridge(model=model, prompt=prompt, run_id=run_id)
    run.status = status
    run.summary = summary[:5000] if summary else ""
    run.output = output[:50000] if output else ""
    run.finished_at = djangotime.now()
    run.save()
    return status


def _ai_alert(agent, label, status, summary, alert_threshold):
    """Create a custom TRMM alert if the verdict meets the threshold."""
    from alerts.models import Alert
    from tacticalrmm.constants import AlertType, AlertSeverity

    if alert_threshold == "never":
        return
    severity = None
    if status == "alert":
        severity = AlertSeverity.ERROR
    elif status == "warning" and alert_threshold == "warning":
        severity = AlertSeverity.WARNING
    elif status == "error":
        severity = AlertSeverity.WARNING
    if severity:
        Alert.objects.create(
            agent=agent,
            alert_type=AlertType.CUSTOM,
            severity=severity,
            message=f"[Pi AI: {label}] {summary}"[:255],
            hidden=False,
        )


@app.task
def run_ai_task(task_id, triggered_by="schedule"):
    """Run one scheduled Pi AI task headlessly via the pi-trmm-bridge, then
    record the result and raise a TRMM alert if the verdict meets the
    threshold."""
    import uuid

    from core.models import AITask, AITaskRun

    try:
        task = AITask.objects.select_related("agent", "model").get(pk=task_id)
    except AITask.DoesNotExist:
        return "not found"

    # Stop-guard: emergency stop drains the backlog as no-ops. (The scheduler
    # already gates on enabled; an explicit Run Now must still execute.)
    if ai_killed():
        return "skipped (stopped)"

    run_id = uuid.uuid4().hex
    run = AITaskRun.objects.create(
        task=task, agent=task.agent, run_id=run_id,
        triggered_by=triggered_by, status="running",
    )

    model = _resolve_ai_model(task.model)
    if not model:
        msg = "No enabled AI model / default configured."
        AITask.objects.filter(pk=task.pk).update(
            last_run=djangotime.now(), last_status="error", last_summary=msg
        )
        run.status = "error"; run.summary = msg; run.finished_at = djangotime.now(); run.save()
        return "no model"

    status, summary, output = _run_prompt_on_agent(
        agent=task.agent, model=model, prompt=task.prompt,
        allow_mutating=task.allow_mutating, run_id=run_id,
    )

    task.last_run = djangotime.now()
    task.last_status = status
    task.last_summary = summary[:5000] if summary else ""
    task.last_output = output[:50000] if output else ""
    fields = ["last_run", "last_status", "last_summary", "last_output"]
    if task.schedule_type == AITask.SCHEDULE_ONCE or task.run_mode == "now":
        # one-shot: disable after run (kept with results)
        task.enabled = False
        task.run_at = None
        task.next_run = None
        fields += ["enabled", "run_at", "next_run"]
    else:
        task.next_run = _compute_task_next_run(task)
        fields += ["next_run"]
    task.save(update_fields=fields)

    run.status = status
    run.summary = summary[:5000] if summary else ""
    run.output = output[:50000] if output else ""
    run.finished_at = djangotime.now()
    run.save()

    _ai_alert(task.agent, task.name, status, summary, task.alert_threshold)
    return f"{status}"


# ---- Bulk AI Command --------------------------------------------------------
# maps a filter field to its ORM lookup path
_BULK_FILTER_FIELDS = {
    "hostname": "hostname",
    "client": "site__client__name",
    "site": "site__name",
    "description": "description",
    "operating_system": "operating_system",
    "plat": "plat",
    "monitoring_type": "monitoring_type",
    # installed software: JSON list on the related InstalledSoftware row.
    # Matched as a case-insensitive substring against the software list
    # (so "contains 'online backup'" finds any machine with a matching entry).
    "software": "installedsoftware__software",
}


def _condition_q(cond):
    """Turn one {field, op, value} condition into a Q object (or None).
    Negations use ~Q so they compose correctly inside OR groups."""
    from django.db.models import Q

    key = cond.get("field")
    field = _BULK_FILTER_FIELDS.get(key)
    op = cond.get("op", "contains")
    value = cond.get("value", "")
    if not field or value == "":
        return None
    # Installed software is a JSON list on a related row; only substring
    # matching is meaningful, so all positive ops become icontains and the
    # negative ops become its negation.
    if key == "software":
        base = Q(**{f"{field}__icontains": value})
        return ~base if op in ("not_contains", "not_equals") else base
    if op == "contains":
        return Q(**{f"{field}__icontains": value})
    if op == "not_contains":
        return ~Q(**{f"{field}__icontains": value})
    if op == "equals":
        return Q(**{f"{field}__iexact": value})
    if op == "not_equals":
        return ~Q(**{f"{field}__iexact": value})
    if op == "startswith":
        return Q(**{f"{field}__istartswith": value})
    return None


def _normalize_filter_groups(filters):
    """Accept both the new grouped shape and the legacy flat shape.
    Legacy: [{field,op,value}, ...] -> a single AND group.
    New:    [{match, conditions:[...]}, ...]."""
    filters = filters or []
    if not filters:
        return []
    first = filters[0]
    if isinstance(first, dict) and "conditions" not in first and (
        "field" in first or "op" in first or "value" in first
    ):
        return [{"match": "all", "conditions": filters}]
    return filters


def _group_q(group):
    match = (group.get("match") or "all").lower()
    qs = [q for q in (_condition_q(c) for c in group.get("conditions", [])) if q is not None]
    if not qs:
        return None
    combined = qs[0]
    for q in qs[1:]:
        combined = (combined & q) if match == "all" else (combined | q)
    return combined


def _apply_bulk_filters(q, filters, group_match="any"):
    """Combine filter GROUPS onto a queryset.
    Within a group conditions are AND/OR'd by the group's own match; the groups
    themselves are AND/OR'd by group_match ("all"=AND, "any"=OR)."""
    groups = _normalize_filter_groups(filters)
    gqs = [gq for gq in (_group_q(g) for g in groups) if gq is not None]
    if not gqs:
        return q.none()  # no effective conditions -> match nothing (fail closed)
    gm = (group_match or "any").lower()
    combined = gqs[0]
    for gq in gqs[1:]:
        combined = (combined & gq) if gm == "all" else (combined | gq)
    # OR across joined fields (client/site names) can duplicate rows
    return q.filter(combined).distinct()


def _has_effective_conditions(filters):
    """True only if at least one filter condition has a known field AND a
    non-empty value. Used to fail CLOSED: a filter target with nothing
    effective must match NOTHING, never every agent."""
    for g in _normalize_filter_groups(filters):
        for c in g.get("conditions", []) or []:
            if _BULK_FILTER_FIELDS.get(c.get("field")) and (c.get("value", "") != ""):
                return True
    return False


# Hard safety cap: a single bulk AI command may never fan out to more than this
# many agents (guards against accidental/mis-scoped targets running up huge LLM
# spend). Override in local_settings.py with PI_BULK_MAX_AGENTS.
def _bulk_max_agents():
    try:
        return int(getattr(settings, "PI_BULK_MAX_AGENTS", 250))
    except (TypeError, ValueError):
        return 250


def _resolve_bulk_targets(cmd):
    """Resolve a bulk command's target selection to a list of ONLINE agents.

    FAILS CLOSED: any target that does not establish a real constraint resolves
    to ZERO agents. Only an explicit target=='all' matches every agent. This
    prevents an empty/mis-scoped filter or a missing client/site from silently
    fanning out to the entire fleet.
    """
    from agents.models import Agent
    from tacticalrmm.constants import AgentMonType, AgentPlat, AGENT_STATUS_ONLINE

    q = Agent.objects.select_related("site__client").defer("services", "wmi_detail")
    target = cmd.target
    if target == "all":
        pass  # explicit whole-fleet target
    elif target == "client":
        if not cmd.client_id:
            return []
        q = q.filter(site__client_id=cmd.client_id)
    elif target == "site":
        if not cmd.site_id:
            return []
        q = q.filter(site_id=cmd.site_id)
    elif target == "agents":
        pks = list(cmd.agents.values_list("pk", flat=True))
        if not pks:
            return []
        q = q.filter(pk__in=pks)
    elif target == "filter":
        filters = getattr(cmd, "filters", None) or []
        if not _has_effective_conditions(filters):
            return []  # empty/ineffective filter -> match nothing (fail closed)
        q = _apply_bulk_filters(
            q, filters, getattr(cmd, "filter_match", None) or "any"
        )
    else:
        return []  # unknown target -> fail closed

    if cmd.mon_type == "servers":
        q = q.filter(monitoring_type=AgentMonType.SERVER)
    elif cmd.mon_type == "workstations":
        q = q.filter(monitoring_type=AgentMonType.WORKSTATION)

    if cmd.os_type in (AgentPlat.WINDOWS, AgentPlat.LINUX, AgentPlat.DARWIN):
        q = q.filter(plat=cmd.os_type)

    # per-machine exclusions: drop specific agents even if they matched
    exclude = set(getattr(cmd, "exclude_agent_ids", None) or [])

    # skip offline agents and excluded agents
    return [
        a
        for a in q
        if a.status == AGENT_STATUS_ONLINE and a.agent_id not in exclude
    ]


def _compute_schedule(
    schedule_type, interval_seconds, run_time, weekly_days, monthly_day, from_time=None
):
    """Generic next-run computer shared by AI tasks and bulk AI commands."""
    import calendar
    import datetime as _dt

    from django.utils import timezone as _tz

    now = _tz.localtime(from_time) if from_time else _tz.localtime()
    if schedule_type == "interval":
        secs = interval_seconds if interval_seconds and interval_seconds > 0 else 3600
        return now + _dt.timedelta(seconds=secs)

    rt = run_time or _dt.time(0, 0)
    base = now.replace(hour=rt.hour, minute=rt.minute, second=0, microsecond=0)

    if schedule_type == "daily":
        return base if base > now else base + _dt.timedelta(days=1)

    if schedule_type == "weekly":
        days = sorted(weekly_days or [])
        if not days:
            days = [now.weekday()]
        for i in range(0, 8):
            cand = base + _dt.timedelta(days=i)
            if cand > now and cand.weekday() in days:
                return cand
        return base + _dt.timedelta(days=7)

    if schedule_type == "monthly":
        day = monthly_day or 1
        year, month = now.year, now.month
        for _ in range(0, 13):
            last = calendar.monthrange(year, month)[1]
            d = min(day, last)
            cand = base.replace(year=year, month=month, day=d)
            if cand > now:
                return cand
            month += 1
            if month > 12:
                month = 1
                year += 1
        return None
    return None


def _compute_bulk_next_run(cmd, from_time=None):
    return _compute_schedule(
        cmd.schedule_type,
        (cmd.interval_hours or 24) * 3600,
        cmd.run_time,
        cmd.weekly_days,
        cmd.monthly_day,
        from_time,
    )


def _compute_task_next_run(task, from_time=None):
    return _compute_schedule(
        task.schedule_type,
        (task.interval_minutes or 60) * 60,
        task.run_time,
        task.weekly_days,
        task.monthly_day,
        from_time,
    )
    return None


@app.task
def dispatch_due_bulk_ai_commands():
    """Poller: queue any bulk AI commands whose next_run has arrived."""
    from core.models import BulkAICommand, CoreSettings

    core = CoreSettings.objects.first()
    if not core or not core.ai_module_enabled:
        return "ai module disabled"

    now = djangotime.now()
    # only recurring (scheduled) commands are auto-fired; "now" ones wait for a
    # manual run and then disable themselves
    for cmd in BulkAICommand.objects.filter(enabled=True, run_mode="schedule"):
        if cmd.next_run is None:
            cmd.next_run = _compute_bulk_next_run(cmd)
            cmd.save(update_fields=["next_run"])
            continue
        if now >= cmd.next_run:
            run_bulk_ai_command.delay(cmd.pk)
    return "ok"


@app.task
def run_bulk_ai_command(cmd_id, triggered_by="bulk"):
    """Fan out a bulk AI command to all ONLINE targeted agents."""
    from core.models import BulkAICommand

    try:
        cmd = BulkAICommand.objects.select_related("model", "client", "site").get(pk=cmd_id)
    except BulkAICommand.DoesNotExist:
        return "not found"

    # a fresh dispatch clears any prior per-command stop (so a disabled/one-shot
    # command can always be re-run manually)
    cmd_stop_clear(cmd_id)

    agents = _resolve_bulk_targets(cmd)

    # Hard safety cap: never fan out to more than the cap. Guards against an
    # accidental/mis-scoped target running up huge LLM spend across the fleet.
    cap = _bulk_max_agents()
    if len(agents) > cap:
        from logs.models import DebugLog

        msg = (
            f"Bulk AI command '{cmd.name}' (id={cmd.pk}) resolved {len(agents)} "
            f"agents which exceeds the safety cap of {cap}; REFUSING to run. "
            f"Narrow the target/filter, or raise PI_BULK_MAX_AGENTS in "
            f"local_settings.py to intentionally allow more."
        )
        try:
            DebugLog.error(message=msg)
        except Exception:
            pass
        cmd.last_run = djangotime.now()
        cmd.last_run_count = 0
        fields = ["last_run", "last_run_count", "next_run"]
        if cmd.run_mode == "now":
            cmd.enabled = False
            cmd.next_run = None
            fields.append("enabled")
        else:
            cmd.next_run = _compute_bulk_next_run(cmd)
        cmd.save(update_fields=fields)
        return f"REFUSED: {len(agents)} agents exceeds cap {cap}"

    import uuid as _uuid

    batch_id = _uuid.uuid4().hex
    if (cmd.report_prompt or "").strip() and agents:
        # run all machines, THEN one finalizer compiles a single combined report
        from celery import chord

        header = [
            run_bulk_ai_agent.s(cmd.pk, agent.pk, triggered_by, batch_id)
            for agent in agents
        ]
        chord(header)(finalize_bulk_report.s(cmd.pk, batch_id))
    else:
        for agent in agents:
            run_bulk_ai_agent.delay(cmd.pk, agent.pk, triggered_by, batch_id)

    cmd.last_run = djangotime.now()
    cmd.last_run_count = len(agents)
    fields = ["last_run", "last_run_count", "next_run"]
    if cmd.run_mode == "now":
        # one-shot: disable after running (kept in the list with its results)
        cmd.enabled = False
        cmd.next_run = None
        fields.append("enabled")
    else:
        cmd.next_run = _compute_bulk_next_run(cmd)
    cmd.save(update_fields=fields)
    return f"queued {len(agents)} agents"


# Global emergency-stop flag (redis). While set, ALL queued AI runner tasks
# no-op instead of calling the LLM - this drains a large backlog that Celery's
# revoke/inspect can't reach (tasks still sitting in the broker queue).
_AI_KILL_KEY = "pi_ai_kill_until"


def ai_kill_set(seconds=900):
    from time import time

    try:
        with from_url(
            f"redis://{settings.REDIS_HOST}:6379", decode_responses=True
        ) as conn:
            conn.set(_AI_KILL_KEY, str(int(time()) + int(seconds)), ex=int(seconds))
    except Exception:
        pass


def ai_kill_clear():
    try:
        with from_url(
            f"redis://{settings.REDIS_HOST}:6379", decode_responses=True
        ) as conn:
            conn.delete(_AI_KILL_KEY)
    except Exception:
        pass


# Per-command stop flag (redis). Set by the per-command Stop action to drain
# that command's queued backlog. Distinct from a command being disabled/spent
# (a one-shot "now" command disables itself after running) - an explicit Run Now
# CLEARS this flag and re-dispatches, so disabled/one-shot commands can always
# be run again manually.
def _cmd_stop_key(cmd_id):
    return f"pi_ai_cmd_stop:{cmd_id}"


def cmd_stop_set(cmd_id, seconds=3600):
    try:
        with from_url(
            f"redis://{settings.REDIS_HOST}:6379", decode_responses=True
        ) as conn:
            conn.set(_cmd_stop_key(cmd_id), "1", ex=int(seconds))
    except Exception:
        pass


def cmd_stop_clear(cmd_id):
    try:
        with from_url(
            f"redis://{settings.REDIS_HOST}:6379", decode_responses=True
        ) as conn:
            conn.delete(_cmd_stop_key(cmd_id))
    except Exception:
        pass


def cmd_stopped(cmd_id):
    try:
        with from_url(
            f"redis://{settings.REDIS_HOST}:6379", decode_responses=True
        ) as conn:
            return bool(conn.get(_cmd_stop_key(cmd_id)))
    except Exception:
        return False


def ai_killed():
    from time import time

    try:
        with from_url(
            f"redis://{settings.REDIS_HOST}:6379", decode_responses=True
        ) as conn:
            raw = conn.get(_AI_KILL_KEY)
        return bool(raw) and time() < float(raw)
    except Exception:
        return False


@app.task
def run_bulk_ai_agent(cmd_id, agent_pk, triggered_by="bulk", batch_id=None):
    """Run a bulk command's prompt on one agent, recording an AITaskRun."""
    import uuid

    from redis import from_url  # noqa: F811
    from agents.models import Agent
    from core.models import BulkAICommand, AITaskRun

    try:
        cmd = BulkAICommand.objects.select_related("model").get(pk=cmd_id)
        agent = Agent.objects.select_related("site__client").get(pk=agent_pk)
    except (BulkAICommand.DoesNotExist, Agent.DoesNotExist):
        return "not found"

    # Stop-guard: re-check at execution time so an emergency-stop or a
    # per-command Stop drains the queued backlog with no LLM calls or alerts.
    # NOTE: we intentionally do NOT skip merely because the command is disabled
    # - a one-shot command disables itself after running, but an explicit Run
    # Now must still execute. Draining is driven by the stop flags instead.
    if ai_killed() or cmd_stopped(cmd_id):
        return "skipped (stopped)"

    model = _resolve_ai_model(cmd.model)
    if not model:
        return "no model"

    run_id = uuid.uuid4().hex
    run = AITaskRun.objects.create(
        bulk=cmd, agent=agent, run_id=run_id, batch_id=batch_id,
        triggered_by=triggered_by, status="running",
    )
    status, summary, output = _run_prompt_on_agent(
        agent=agent, model=model, prompt=cmd.prompt,
        allow_mutating=cmd.allow_mutating, run_id=run_id,
    )
    run.status = status
    run.summary = summary[:5000] if summary else ""
    run.output = output[:50000] if output else ""
    run.finished_at = djangotime.now()
    run.save()

    _ai_alert(agent, cmd.name, status, summary, cmd.alert_threshold)
    return f"{status}"
