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
            # Advance the schedule BEFORE queueing, not after the run finishes.
            # beat fires every minute while a run can take several minutes, so a
            # next_run left in the past re-queues the same task once per minute of
            # its own runtime (measured: 1.8x-9.0x duplicate dispatches per slot).
            # This also stops the infinite re-dispatch of a task whose run aborts
            # early (e.g. no model configured) and so never reaches the completion
            # path that used to be the only place next_run was advanced.
            # Trade-off: a task that crashes mid-run waits for its next slot rather
            # than retrying. Deliberate - silent duplicate work is worse than a
            # skipped cycle, and duplicates here mean duplicate customer contact.
            if task.schedule_type == AITask.SCHEDULE_ONCE:
                task.run_at = None
                task.save(update_fields=["run_at"])
            else:
                task.next_run = _compute_task_next_run(task)
                task.save(update_fields=["next_run"])
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
        "ai_notes": agent.ai_notes or "",
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
            bool(data.get("ticket_error")),
        )
    except _requests.exceptions.Timeout:
        recovered = _recover_ai_run_from_redis(run_id)
        if recovered and recovered.get("status") not in (None, "running"):
            return (
                recovered["status"],
                recovered.get("summary") or "(recovered after HTTP timeout)",
                recovered.get("transcript") or "",
                bool(recovered.get("ticket_error")),
            )
        return (
            "error",
            f"Run exceeded PI_RUN_TIMEOUT ({run_timeout}s) and did not finish.",
            "",
            False,
        )
    except Exception as e:
        return ("error", f"Bridge error: {e}", "", False)


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
        return (
            data.get("status", "error"),
            data.get("summary", ""),
            data.get("transcript", ""),
            bool(data.get("ticket_error")),
        )
    except Exception as e:
        return ("error", f"Report bridge call failed: {e}", "", True)


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
    status, summary, output, ticket_error = _run_report_on_bridge(
        model=model, prompt=prompt, run_id=run_id
    )
    run.status = status
    run.summary = summary[:5000] if summary else ""
    run.output = output[:50000] if output else ""
    run.finished_at = djangotime.now()
    run.save()
    # Only surface a TRMM alert if the combined report itself failed to file.
    if ticket_error or status == "error":
        _ai_alert_gated(
            runs[0].agent if runs else None,
            f"{cmd.name} (report)",
            status,
            f"combined report NOT filed: {summary}",
            "alert",
            True,
        )
    return status


def _ai_alert_gated(agent, label, status, summary, alert_threshold, ticket_error):
    """Alerting policy for AI tasks/bulk. When CoreSettings.ai_alerts_only_on_ticket_error
    is set, suppress the normal warning/alert TRMM alerts (tickets handle those) and
    raise a TRMM alert ONLY if the AI failed to file its ticket, or the run errored."""
    core = get_core_settings()
    if getattr(core, "ai_alerts_only_on_ticket_error", False):
        if ticket_error or status == "error":
            _ai_alert(
                agent,
                label,
                "alert",
                f"[ACTION NEEDED: ticket NOT filed] {summary}",
                "alert",
            )
        return
    _ai_alert(agent, label, status, summary, alert_threshold)


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

    status, summary, output, ticket_error = _run_prompt_on_agent(
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

    _ai_alert_gated(task.agent, task.name, status, summary, task.alert_threshold, ticket_error)
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
            # Advance before queueing - same dispatch race as dispatch_due_ai_tasks.
            cmd.next_run = _compute_bulk_next_run(cmd)
            cmd.save(update_fields=["next_run"])
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
    status, summary, output, ticket_error = _run_prompt_on_agent(
        agent=agent, model=model, prompt=cmd.prompt,
        allow_mutating=cmd.allow_mutating, run_id=run_id,
    )
    run.status = status
    run.summary = summary[:5000] if summary else ""
    run.output = output[:50000] if output else ""
    run.finished_at = djangotime.now()
    run.save()

    _ai_alert_gated(agent, cmd.name, status, summary, cmd.alert_threshold, ticket_error)
    return f"{status}"


# ---------------------------------------------------------------------------
# AI ticket automation (helpdesk-agnostic add-on).
# Phase 1 = SHADOW mode: poll the helpdesk via the admin-defined helpdesk.js
# (list_open_tickets op), scope-limit deterministically, and for each in-scope
# NEW ticket run a triage session that only CLASSIFIES and posts a staff-only
# internal note draft. No closes, no replies, no device actions.
# ---------------------------------------------------------------------------

def _ai_ticket_scope_conf(core):
    import json

    try:
        conf = json.loads(core.ai_ticket_scope or "{}")
    except Exception:
        conf = {}
    return {
        # Look at (triage) everything eligible (unassigned or bot-assigned), any domain.
        "look_at_all": bool(conf.get("look_at_all_unassigned", conf.get("look_at_all", False))),
        # Only these domains get AUTO-ACTIONED (cancel/claim/tag); others are look-only.
        "act_domains": [d.strip().lower() for d in conf.get("auto_action_domains", []) if d.strip()],
        # Resolved-client names that also authorise auto-action (covers infra alerts
        # with no requester domain, e.g. monitoring alerts for a test client).
        "act_clients": [c.strip() for c in conf.get("auto_action_clients", []) if c.strip()],
        # Back-compat: an explicit look-list still triaged when look_at_all is false.
        "look_domains": [d.strip().lower() for d in conf.get("work_regular_ticket_if_requester_domain_in", []) if d.strip()],
        "alerts_always": bool(conf.get("always_look_at_alerts", conf.get("always_work_alert_tickets", True))),
        "alert_subject_prefixes": [p for p in (conf.get("alert_ticket_match", {}) or {}).get("subject_starts_with", []) if p],
        "alert_from_domains": [d.strip().lower() for d in (conf.get("alert_ticket_match", {}) or {}).get("from_email_domains", []) if d.strip()],
    }


def _ticket_is_alert(t, scope):
    subj = (t.get("subject") or "").strip()
    dom = ((t.get("requester_email") or "").split("@")[-1] or "").lower()
    if any(subj.startswith(p) for p in scope["alert_subject_prefixes"]):
        return True
    return bool(dom and dom in scope["alert_from_domains"])


def _ticket_in_scope(t, scope, is_alert):
    # Triage scope = which tickets we LOOK AT. Acting is decided separately.
    if scope["look_at_all"]:
        return True
    if is_alert:
        return scope["alerts_always"]
    dom = ((t.get("requester_email") or "").split("@")[-1] or "").lower()
    return bool(dom and dom in scope["look_domains"])



@app.task
def poll_helpdesk_tickets():
    """Beat task (~90s): list open tickets via helpdesk.js, reconcile against
    AITicketState, enqueue triage for new in-scope tickets. First-ever poll
    baselines the existing backlog WITHOUT triaging it (no note spam)."""
    import requests as _requests

    from core.models import AITicketState
    from logs.models import DebugLog

    core = get_core_settings()
    if not (core.ai_module_enabled and core.ai_ticket_automation_enabled):
        return "disabled"
    if not ((core.ai_helpdesk_code or "").strip() and (core.ai_helpdesk_api_base_url or "").strip()):
        return "no helpdesk integration configured"

    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    try:
        r = _requests.post(
            f"{bridge}/pi/tickets/poll",
            json={
                "helpdesk_api": {
                    "base_url": core.ai_helpdesk_api_base_url or "",
                    "api_key": core.ai_helpdesk_api_key or "",
                },
                "helpdesk_code": core.ai_helpdesk_code or "",
            },
            timeout=(10, 120),
        )
        data = r.json()
    except Exception as e:
        DebugLog.error(message=f"AI ticket poll failed: {e}")
        return f"poll error: {e}"
    if data.get("error"):
        DebugLog.error(message=f"AI ticket poll failed: {data['error']}")
        return f"poll error: {data['error']}"

    tickets = data.get("tickets") or []
    scope = _ai_ticket_scope_conf(core)
    baseline = not AITicketState.objects.exists()
    seen, enqueued = 0, 0
    for t in tickets:
        ref = str(t.get("ref") or "").strip()
        if not ref:
            continue
        seen += 1
        is_alert = _ticket_is_alert(t, scope)
        in_scope = _ticket_in_scope(t, scope, is_alert)
        last_msg = int(t.get("last_msg_id") or 0)
        msg_from_bot = bool(t.get("last_msg_bot"))
        assignee = str(t.get("assignee_id") or "")
        # Tickets THIS system filed as internal notices for a human to read (model
        # catalog changes, etc). They are NOT customer tickets and NOT alerts: there is
        # nothing to diagnose and nothing to close. Previously they went through normal
        # triage, the model classified them "alert_clean", and the deterministic DECIDE
        # step cancelled them within a minute - so the notice was closed before anyone
        # read it. For the urgent variant ("a model you have configured disappeared")
        # that would have silently swallowed an outage warning.
        #
        # They are now classified deterministically and never sent to the model at all,
        # which is what MANDATE 4.8 requires: closing is not a judgement call. WHICH
        # tickets are notices is decided deployment-side (helpdesk.js sets
        # internal_notice), so product code stays helpdesk-agnostic - MANDATE 4.11.
        notice = bool(t.get("internal_notice"))
        st, created = AITicketState.objects.get_or_create(
            ticket_ref=ref,
            defaults={
                "subject": (t.get("subject") or "")[:400],
                "requester": (t.get("requester_email") or "")[:255],
                "is_alert": is_alert,
                "last_change_seen": str(t.get("write_date") or "")[:64],
                "last_message_id": last_msg,
                "assignee_seen": assignee,
                "classification": "info" if notice else "",
                "status": (
                    "baseline" if baseline
                    else ("info_for_human" if notice
                          else ("new" if in_scope else "skipped_out_of_scope"))
                ),
            },
        )
        if baseline:
            continue
        # An internal notice is never triaged, never re-triaged and never auto-closed.
        # It stays open and unassigned until a human deals with it.
        if notice:
            if st.status != "info_for_human" or st.classification != "info":
                st.status = "info_for_human"
                st.classification = "info"
                st.save(update_fields=["status", "classification"])
                # A notice owned by the bot LOOKS handled, so nobody picks it up. Release
                # it once, on the transition only, so it shows as unassigned and waiting.
                # release_ticket is defined to touch ONLY bot-owned tickets, never a
                # human's, so this can never take a ticket off a technician.
                try:
                    _requests.post(
                        f"{bridge}/pi/helpdesk-op",
                        json={
                            "operation": "release_ticket",
                            "args": {"ticket": ref},
                            "helpdesk_api": {
                                "base_url": core.ai_helpdesk_api_base_url or "",
                                "api_key": core.ai_helpdesk_api_key or "",
                            },
                            "helpdesk_code": core.ai_helpdesk_code or "",
                        },
                        timeout=(5, 30),
                    )
                except Exception:
                    pass  # best-effort: an unreleased notice is still visible, just owned
            continue
        if created:
            if st.status == "new":
                triage_ai_ticket.delay(st.pk)
                enqueued += 1
            continue
        # ---- re-engage loop: existing ticket. Re-triage when there's NEW activity
        # from a non-AI author (customer/tech reply, or a tech handing it back).
        if st.status == "triaging":
            continue  # in progress
        new_activity = last_msg > (st.last_message_id or 0) and not msg_from_bot
        # advance markers (also past the AI's own messages -> no self-loop). Only save
        # when something actually changed, so a dormant ticket isn't re-written (and its
        # "last worked" timestamp isn't bumped) on every poll.
        new_lmid = max(last_msg, st.last_message_id or 0)
        new_lcs = str(t.get("write_date") or "")[:64]
        changed = (
            new_lmid != (st.last_message_id or 0)
            or st.assignee_seen != assignee
            or st.is_alert != is_alert
            or st.last_change_seen != new_lcs
        )
        st.last_message_id = new_lmid
        st.assignee_seen = assignee
        st.is_alert = is_alert
        st.last_change_seen = new_lcs
        if new_activity and in_scope:
            st.status = "new"
            st.save()
            triage_ai_ticket.delay(st.pk, force=True)
            enqueued += 1
        elif changed:
            # bookkeeping only - do NOT bump the AI "last worked" (updated/last_triaged)
            st.save(update_fields=["last_message_id", "assignee_seen", "is_alert", "last_change_seen"])
    return f"seen {seen}, enqueued {enqueued}{' (baseline)' if baseline else ''}"


@app.task
def triage_ai_ticket(state_pk, force=False):
    """Run ONE triage session for a ticket. force=True re-triages a ticket that was
    already handled (used by the re-engage loop when a customer/tech replies)."""
    import requests as _requests

    from core.models import AITicketState

    core = get_core_settings()
    if not (core.ai_module_enabled and core.ai_ticket_automation_enabled):
        return "disabled"
    try:
        st = AITicketState.objects.get(pk=state_pk)
    except AITicketState.DoesNotExist:
        return "gone"
    if not force and st.status not in ("new", "error"):
        return f"skip status={st.status}"
    model = _resolve_ai_model(None)
    if not model:
        st.status = "error"
        st.error_detail = "no enabled AI model/default configured"
        st.save(update_fields=["status", "error_detail"])
        return st.error_detail

    st.status = "triaging"
    st.save(update_fields=["status"])
    scope = _ai_ticket_scope_conf(core)
    from django.utils.crypto import get_random_string

    from core.models import AIDecisionRequest

    # ONE durable chat thread per ticket: reuse an existing thread's token (any
    # status) so close->reopen keeps the full history under the same link.
    _existing = AIDecisionRequest.objects.filter(ticket_ref=st.ticket_ref).order_by("-updated").first()
    decision_token = _existing.token if _existing else get_random_string(32)
    base_url = (
        settings.CORS_ORIGIN_WHITELIST[0]
        if getattr(settings, "CORS_ORIGIN_WHITELIST", None) else ""
    )
    decision_url = f"{base_url}/ai-decision/{decision_token}" if base_url else ""
    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    run_timeout = getattr(settings, "PI_RUN_TIMEOUT", 3600)

    # ---- ALERT VERIFIERS ---------------------------------------------------
    # Before the model is asked to judge a machine-generated alert from its TEXT, go
    # look at the machine. An admin rule (verifiers.js) gathers read-only evidence and
    # rules on it in code. A proven-harmless alert is cancelled here and never costs an
    # LLM call; a proven-real one is pinned open so triage cannot later dismiss it.
    verified_fact, forbid_cancel = "", False
    if core.ai_verifiers_enabled and (core.ai_verifier_code or "").strip():
        try:
            vres = _requests.post(
                f"{bridge}/pi/verify-alert",
                json={
                    "ticket_ref": st.ticket_ref,
                    "verifier_code": core.ai_verifier_code or "",
                    "dry_run": bool(core.ai_verifiers_dry_run),
                    "decision_url": decision_url,
                    "helpdesk_api": {
                        "base_url": core.ai_helpdesk_api_base_url or "",
                        "api_key": core.ai_helpdesk_api_key or "",
                    },
                    "helpdesk_code": core.ai_helpdesk_code or "",
                },
                timeout=(10, 420),
            ).json()
        except Exception as e:
            vres = {"matched": False, "error": f"verify bridge error: {e}"}
        if vres.get("matched"):
            act = vres.get("action") or "human"
            reason = (vres.get("reason") or "")[:5000]
            # Proven harmless AND allowed to act -> already cancelled with its evidence.
            # Stop here: no LLM triage needed for a ticket that is already closed.
            if vres.get("cancelled"):
                st.status = "cancelled_clean"
                st.classification = "alert_clean"
                st.summary = reason
                st.proposed_action = f"Verified on {vres.get('host') or 'the device'}: no action needed. Cancelled automatically."
                st.error_detail = ""
                st.save(update_fields=["status", "classification", "summary",
                                       "proposed_action", "error_detail"])
                return f"verified-cancelled ({vres.get('verifier')})"
            # Anything not proven harmless must never be auto-cancelled downstream.
            if act in ("actionable", "human"):
                forbid_cancel = True
            verified_fact = f"[{vres.get('verifier')}] verdict={act} on {vres.get('host') or '?'} - {reason}"[:4000]

    try:
        r = _requests.post(
            f"{bridge}/pi/ticket-triage",
            json={
                "ticket_ref": st.ticket_ref,
                "is_alert": st.is_alert,
                "requester_email": st.requester or "",
                "provider": model.provider.name,
                "model_id": model.model_id,
                "api_key": model.provider.api_key,
                "thinking_level": model.thinking_level,
                "triage_prompt": core.ai_ticket_triage_prompt or "",
                "act_enabled": bool(core.ai_ticket_act_on_alerts),
                "act_domains": scope["act_domains"],
                "act_clients": scope["act_clients"],
                "decision_url": decision_url,
                "correct_partner": not st.partner_checked,
                "verified_fact": verified_fact,
                "forbid_cancel": forbid_cancel,
                "helpdesk_api": {
                    "base_url": core.ai_helpdesk_api_base_url or "",
                    "api_key": core.ai_helpdesk_api_key or "",
                },
                "helpdesk_code": core.ai_helpdesk_code or "",
            },
            timeout=(10, min(run_timeout, 900)),
        )
        data = r.json()
    except Exception as e:
        st.status = "error"
        st.error_detail = f"bridge error: {e}"
        st.save(update_fields=["status", "error_detail"])
        return st.error_detail

    if data.get("error"):
        st.status = "error"
        st.error_detail = str(data["error"])[:2000]
    else:
        action = data.get("action") or "shadow_note"
        st.status = {
            "cancelled": "cancelled_clean",
            "claimed": "actionable_claimed",
            "flagged_actionable": "actionable_unassigned",
            "needs_input": "needs_input",
        }.get(action, "triaged")
        st.classification = (data.get("classification") or "unknown")[:40]
        st.summary = (data.get("summary") or "")[:5000]
        st.proposed_action = (data.get("proposed_action") or "")[:5000]
        st.error_detail = ""
        # One-time company/contact correction done (or company confidently resolved)
        # -> don't re-correct on later re-triages (respect manual edits).
        if data.get("company_resolved"):
            st.partner_checked = True
        # Persist the chat thread for EVERY triaged ticket (we post a chat link on
        # every note now), reusing the durable per-ticket thread; never lose history.
        if decision_url:
            from django.utils import timezone as _tz

            entry = {"role": "assistant", "content": st.proposed_action or st.summary,
                     "ts": _tz.now().isoformat()}
            ctx = {"client": data.get("client") or "", "affected_device": data.get("affected_device") or "",
                   "classification": st.classification, "summary": st.summary, "requester": st.requester}
            dr = AIDecisionRequest.objects.filter(token=decision_token).first()
            if dr:
                dr.status = "open"
                dr.question = st.proposed_action or dr.question
                dr.context = ctx
                dr.messages = (dr.messages or []) + [entry]
                dr.save()
            else:
                AIDecisionRequest.objects.create(
                    token=decision_token, ticket_ref=st.ticket_ref,
                    question=st.proposed_action, context=ctx, messages=[entry], status="open",
                )
    # Mark when the AI actually worked this ticket (drives the console's "Last worked").
    from django.utils import timezone as _tznow
    st.last_triaged = _tznow.now()
    st.save()
    return f"{st.ticket_ref}: {st.status} {st.classification}"


# ---------------------------------------------------------------------------
# AI scheduled actions: run a future AI action ONCE at its due time. A cheap
# beat dispatcher (a DB timestamp check - no LLM) fires it; execution reuses the
# device-run path so the AI can do the work AND update the ticket. Deleted on
# success; kept (status=error) on failure for review.
# ---------------------------------------------------------------------------

@app.task
def dispatch_due_ai_scheduled_actions():
    """Beat (~1 min): enqueue any scheduled AI actions whose time has come."""
    from django.utils import timezone as djangotime

    from core.models import AIScheduledAction

    core = get_core_settings()
    if not core.ai_module_enabled:
        return "ai disabled"
    now = djangotime.now()
    due = list(
        AIScheduledAction.objects.filter(status="scheduled", run_at__lte=now).values_list("pk", flat=True)[:20]
    )
    for pk in due:
        run_ai_scheduled_action.delay(pk)
    return f"dispatched {len(due)}"


@app.task
def attempt_ai_ticket_resolve(ticket_ref):
    """Ticket Console 'auto-resolve': run a one-shot, READ-ONLY AI attempt on the
    ticket (no customer email, no close, no disruptive changes). The AI posts an
    internal note (RESOLVED-pending-sign-off + draft reply, OR the exact human steps);
    we also append its output to the decision thread so the console shows it."""
    import requests as _requests

    from core.models import AIDecisionRequest, AITicketState

    core = get_core_settings()
    if not (core.ai_module_enabled and (core.ai_helpdesk_code or "").strip()):
        return "disabled"
    st = AITicketState.objects.filter(ticket_ref=ticket_ref).first()
    dr = AIDecisionRequest.objects.filter(ticket_ref=ticket_ref).order_by("-id").first()
    model = _resolve_ai_model(None)
    if not model:
        return "no model"
    ctx = (dr.context if dr else None) or {"summary": (st.summary if st else "")}
    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    try:
        r = _requests.post(
            f"{bridge}/pi/ticket-resolve",
            json={
                "ticket_ref": ticket_ref, "context": ctx,
                "decision_prompt": core.ai_ticket_decision_prompt or "",
                "provider": model.provider.name, "model_id": model.model_id,
                "api_key": model.provider.api_key, "thinking_level": model.thinking_level,
                "helpdesk_api": {
                    "base_url": core.ai_helpdesk_api_base_url or "",
                    "api_key": core.ai_helpdesk_api_key or "",
                },
                "helpdesk_code": core.ai_helpdesk_code or "",
            },
            timeout=(10, 600),
        )
        data = r.json()
    except Exception as e:
        return f"resolve error: {e}"
    out = data.get("output") or (f"(error) {data['error']}" if data.get("error") else "(no output)")
    if dr:
        from django.utils import timezone as _tz

        dr.messages = (dr.messages or []) + [
            {"role": "assistant", "content": out, "ts": _tz.now().isoformat()}
        ]
        dr.status = "open"
        dr.save(update_fields=["messages", "status", "updated"])
    if st:
        st.proposed_action = (out or "")[:5000]
        st.save(update_fields=["proposed_action", "updated"])
    return "ok"


@app.task
def run_ai_scheduled_action(pk):
    """Execute one due scheduled action on its device, update the ticket, then
    delete the job (or mark error)."""
    from core.models import AIScheduledAction

    act = AIScheduledAction.objects.filter(pk=pk).first()
    if not act or act.status != "scheduled":
        return "skip"
    act.status = "running"
    act.save(update_fields=["status", "updated"])
    model = _resolve_ai_model(None)
    if not model:
        act.status = "error"
        act.result = "no enabled AI model/default configured"
        act.save(update_fields=["status", "result", "updated"])
        return act.result
    if not act.agent:
        act.status = "error"
        act.result = "scheduled action has no target device"
        act.save(update_fields=["status", "result", "updated"])
        return act.result

    prompt = act.action
    if act.ticket_ref:
        prompt += (
            f"\n\nThis is scheduled work for {act.ticket_ref}. When finished, FINISH the ticket via the "
            f"helpdesk resolve_ticket operation with (1) internal_note = a review of exactly what you "
            f"did, and (2) customer_html = a polished, friendly HTML reply (inline styles) telling the "
            f"customer it's resolved and what was done. For a pure monitoring alert with no human "
            f"requester, internal_note only (or cancel=true for junk). Never delete data."
        )
    status, summary, output, ticket_error = _run_prompt_on_agent(
        agent=act.agent, model=model, prompt=prompt,
        allow_mutating=act.allow_mutating, run_id=f"sched-{act.pk}",
    )
    if status == "error":
        act.status = "error"
        act.result = (summary or "run error")[:5000]
        act.save(update_fields=["status", "result", "updated"])
        return f"error: {summary}"
    # success -> delete the job (user preference: remove on completion)
    ref = act.ticket_ref
    act.delete()
    return f"done + deleted (ticket {ref or 'n/a'}): {(summary or '')[:120]}"


# ---------------------------------------------------------------------------
# AI Procedures miner: learn reusable, helpdesk-agnostic PROCEDURES (symptom ->
# root cause -> fix -> verify) from how tickets actually get closed. First run
# backfills `ai_procedures_backfill_days`; later runs are incremental since
# last_mined. Fully gated by Global Settings; a no-op unless enabled. The LLM
# distillation happens in the bridge (/pi/mine-procedures); this task owns the
# window, the schedule gate, and the dedup/merge into AIProcedure rows.
# ---------------------------------------------------------------------------

def _match_existing_procedure(title, cat, update_code):
    """Find the procedure this mined item should UPDATE (if any): explicit code first,
    then exact title+category, then a fuzzy title match within the same category."""
    import difflib

    from core.models import AIProcedure

    if update_code:
        digits = "".join(ch for ch in str(update_code) if ch.isdigit())
        if digits:
            t = AIProcedure.objects.filter(id=int(digits)).first()
            if t:
                return t
    t = AIProcedure.objects.filter(title__iexact=title, category__iexact=cat).first()
    if t:
        return t
    best, best_r = None, 0.0
    tl = title.lower()
    for cand in AIProcedure.objects.filter(category__iexact=cat).only("id", "title"):
        r = difflib.SequenceMatcher(None, tl, (cand.title or "").lower()).ratio()
        if r > best_r:
            best, best_r = cand, r
    return best if best_r >= 0.82 else None


def _procedure_confidence(p):
    """Cheap, transparent confidence: approved + seen a few times = high. This is what
    later gates auto-resolution (only high-confidence, approved procedures qualify)."""
    n = p.occurrence_count or 1
    if p.status == "approved" and n >= 3:
        return "high"
    if n >= 3 or p.status == "approved":
        return "medium"
    return "low"


@app.task
def mine_ticket_procedures(force=False, chain=False):
    from datetime import timedelta

    import requests as _requests
    from django.utils import timezone as djangotime

    from core.models import AIMinedTicket, AIProcedure

    core = get_core_settings()
    # Library must be enabled. The SCHEDULED run also needs mining_enabled + interval;
    # a manual force=True run (the 'Mine now' button) bypasses both - the admin asked for it.
    if not (core.ai_module_enabled and core.ai_procedures_enabled):
        return "disabled"
    if not (core.ai_helpdesk_code or "").strip():
        return "no helpdesk integration configured"
    now = djangotime.now()
    if not force:
        if not core.ai_procedures_mining_enabled:
            return "scheduled mining disabled"
        interval = timedelta(hours=max(1, core.ai_procedures_interval_hours or 24))
        if core.ai_procedures_last_mined and (now - core.ai_procedures_last_mined) < interval:
            return "not due"
    # Always look back over the configured window; the per-ticket dedup ledger (below)
    # decides what actually gets mined, so re-scanning is cheap and never double-processes.
    since = now - timedelta(days=max(1, core.ai_procedures_backfill_days or 120))
    model = _resolve_ai_model(None)
    if not model:
        return "no model"
    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    run_timeout = getattr(settings, "PI_RUN_TIMEOUT", 3600)
    try:
        r = _requests.post(
            f"{bridge}/pi/mine-procedures",
            json={
                "since": since.isoformat(),
                # Dedup ledger: {ticket_ref: last_change_seen}. The bridge mines only
                # tickets that are new or changed since we last looked at them.
                "seen": dict(AIMinedTicket.objects.values_list("ticket_ref", "last_change_seen")),
                # Existing procedures so the model can UPDATE a match (via update_code)
                # instead of creating a near-duplicate.
                "existing": [
                    {"code": f"{p['id']:07d}", "title": p["title"], "category": p["category"]}
                    for p in AIProcedure.objects.values("id", "title", "category")[:1500]
                ],
                "provider": model.provider.name,
                "model_id": model.model_id,
                "api_key": model.provider.api_key,
                "thinking_level": model.thinking_level,
                "mining_prompt": core.ai_procedures_mining_prompt or "",
                "helpdesk_api": {
                    "base_url": core.ai_helpdesk_api_base_url or "",
                    "api_key": core.ai_helpdesk_api_key or "",
                },
                "helpdesk_code": core.ai_helpdesk_code or "",
            },
            timeout=(10, min(run_timeout, 1800)),
        )
        data = r.json()
    except Exception as e:
        return f"bridge error: {e}"
    if data.get("error"):
        return f"miner error: {str(data['error'])[:300]}"
    procs = data.get("procedures") or []
    created = updated = 0
    for p in procs:
        title = (p.get("title") or "").strip()
        if not title:
            continue
        from core.models import normalize_procedure_category

        cat = normalize_procedure_category(p.get("category"))[:100]
        refs = [str(x) for x in (p.get("source_ticket_refs") or [])]
        # dedup/merge target: (1) the model's explicit update_code, (2) exact title+cat,
        # (3) fuzzy title within the same category - so we UPDATE a similar procedure
        # instead of piling on near-duplicates.
        existing = _match_existing_procedure(title, cat, p.get("update_code"))
        if existing:
            merged = list(dict.fromkeys((existing.source_ticket_refs or []) + refs))
            existing.source_ticket_refs = merged
            existing.occurrence_count = max(existing.occurrence_count, len(merged) or existing.occurrence_count)
            existing.last_seen = now
            # Never overwrite a human's edits: for approved/human procedures only FILL
            # BLANKS. But a machine-mined DRAFT that no one has curated yet may absorb a
            # richer version - e.g. re-mining with the ticket's live ai-decision session
            # now yields the EXACT commands the tech ran, so take the more detailed value.
            draft_mined = existing.origin == "ai_mined" and existing.status == "draft"
            for f in ("symptom", "root_cause", "fix", "verification", "applies_to"):
                nv = (p.get(f) or "").strip()
                cur = (getattr(existing, f) or "").strip()
                if not nv:
                    continue
                if not cur or (draft_mined and len(nv) > len(cur)):
                    setattr(existing, f, nv)
            existing.confidence = _procedure_confidence(existing)
            existing.save()
            updated += 1
        else:
            obj = AIProcedure.objects.create(
                title=title[:300], category=cat, applies_to=(p.get("applies_to") or "")[:400],
                symptom=p.get("symptom") or "", root_cause=p.get("root_cause") or "",
                fix=p.get("fix") or "", verification=p.get("verification") or "",
                source_ticket_refs=refs, occurrence_count=max(1, len(refs)),
                first_seen=now, last_seen=now, origin="ai_mined", status="draft",
            )
            obj.confidence = _procedure_confidence(obj)
            obj.save(update_fields=["confidence"])
            created += 1
    # Update the dedup ledger for EVERY ticket we looked at this run (even if it
    # produced no procedure), so unchanged tickets are skipped next time.
    for m in (data.get("mined") or []):
        ref = m.get("ref")
        if ref:
            AIMinedTicket.objects.update_or_create(
                ticket_ref=ref, defaults={"last_change_seen": m.get("write_date") or ""}
            )
    core.ai_procedures_last_mined = now
    core.save(update_fields=["ai_procedures_last_mined"])
    looked = len(data.get("mined") or [])
    # Self-chain: if this was a chained/forced backfill and there are still tickets left
    # in the window (and the user didn't hit Stop), queue the next batch automatically.
    more = bool(data.get("more")) and not data.get("stopped")
    if (force or chain) and more:
        mine_ticket_procedures.apply_async(kwargs={"force": True, "chain": True}, countdown=8)
    return (
        f"mined {created} new / {updated} updated from {looked} changed tickets "
        f"(window since {since.date()}){'; chaining next batch' if ((force or chain) and more) else ''}"
    )


# ---------------------------------------------------------------------------
# MODEL CATALOG WATCH
# Providers add and retire models without notice. A retired model that we still
# have configured is an outage in waiting: every AI task pointed at it fails.
# This task owns only the mechanical part - read what each provider offers now,
# diff it against the last snapshot, and hand the difference to the deployment's
# own helpdesk code. It deliberately does NOT decide what the ticket says, who it
# is filed against, or how it dedupes: that is `report_model_changes` in
# helpdesk.js, so a change in reporting needs no product change.
# ---------------------------------------------------------------------------
@app.task
def refresh_ai_model_catalog(force=False):
    import json
    from datetime import timedelta

    import requests as _requests
    from django.utils import timezone as djangotime

    from core.models import AIModel, AIProvider

    core = get_core_settings()
    if not core.ai_module_enabled:
        return "ai module disabled"
    if not (force or core.ai_model_catalog_enabled):
        return "catalog watch disabled"
    now = djangotime.now()
    if not force:
        interval = timedelta(hours=max(1, core.ai_model_catalog_interval_hours or 24))
        if core.ai_model_catalog_checked and (now - core.ai_model_catalog_checked) < interval:
            return "not due"

    providers = [
        {"name": p.name, "api_key": p.api_key, "base_url": p.base_url}
        for p in AIProvider.objects.filter(enabled=True)
        if p.api_key
    ]
    if not providers:
        return "no enabled providers with keys"
    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    # probe=True asks each PROVIDER what it serves today (the authoritative answer) and
    # merges that with what the installed runtime can run. Without the probe this only ever
    # saw the runtime's bundled list, so a model released upstream was invisible until
    # someone upgraded the package - which is the whole failure this watch exists to catch.
    try:
        r = _requests.post(
            f"{bridge}/pi/models", json={"providers": providers, "probe": True}, timeout=(10, 180)
        )
        data = r.json()
    except Exception as e:
        return f"bridge error: {e}"
    if data.get("error"):
        return f"discovery error: {str(data['error'])[:200]}"

    rows = data.get("models") or []
    provider_errors = data.get("provider_errors") or {}
    # current[provider] = {model_id: display_name}   (the snapshot shape, unchanged)
    current = {}
    for m in rows:
        prov, mid = m.get("provider") or "", m.get("model_id") or ""
        if prov and mid:
            current.setdefault(prov, {})[mid] = m.get("display_name") or mid
    if not current:
        return "provider returned an empty catalog - not overwriting the snapshot"

    # AVAILABLE-BUT-NOT-RUNNABLE: the provider serves it, the runtime does not know it.
    # Registering it makes it selectable today instead of after the next package upgrade.
    unusable = [m for m in rows if m.get("usable") is False]
    registered, register_note = [], ""
    if unusable and core.ai_model_autoregister:
        try:
            rg = _requests.post(
                f"{bridge}/pi/models/register",
                json={"providers": providers, "models": [
                    {"provider": m["provider"], "model_id": m["model_id"],
                     "display_name": m.get("display_name")} for m in unusable
                ]},
                timeout=(10, 120),
            ).json()
            registered = rg.get("registered") or []
            if rg.get("error"):
                register_note = f" (register error: {str(rg['error'])[:120]})"
        except Exception as e:
            register_note = f" (register failed: {str(e)[:120]})"
        if registered:
            reg_ids = {(m["provider"], m["model_id"]) for m in registered}
            for m in rows:
                if (m.get("provider"), m.get("model_id")) in reg_ids:
                    m["usable"] = True

    try:
        previous = json.loads(core.ai_model_catalog or "{}")
    except Exception:
        previous = {}

    first_run = not previous

    def _flat(cat):
        return {(p, mid) for p, mids in (cat or {}).items() for mid in mids}

    cur_set, prev_set = _flat(current), _flat(previous)
    added = sorted(cur_set - prev_set)
    removed = sorted(prev_set - cur_set)

    # THE OPERATIONALLY SERIOUS CASE: a model we have configured is gone at the PROVIDER.
    # Judged from the provider's own answer (live_at_provider), not from the runtime's
    # bundled list - a package can keep listing a model for years after it stops working.
    # live_at_provider is None when that provider's discovery failed; we then say nothing
    # rather than mistake an API outage for a mass retirement.
    live_lookup = {}
    for m in rows:
        live_lookup[(m.get("provider"), m.get("model_id"))] = m.get("live_at_provider")
    retired_in_use = []
    for am in AIModel.objects.select_related("provider").all():
        if am.provider.name in provider_errors:
            continue  # discovery failed for this provider - do not guess
        if am.provider.name not in current:
            continue  # provider not queried this run
        if live_lookup.get((am.provider.name, am.model_id)) is False or (
            am.model_id not in current.get(am.provider.name, {})
        ):
            retired_in_use.append({
                "provider": am.provider.name,
                "model_id": am.model_id,
                "display_name": am.display_name,
                "enabled": am.enabled,
                "is_default": am.is_default,
            })

    # Informational: the runtime still offers these, but the provider no longer does. Not
    # urgent (nothing here is configured) - it rides along when a ticket is warranted.
    stale_runtime = [
        {"provider": m["provider"], "model_id": m["model_id"]}
        for m in rows if m.get("live_at_provider") is False
        and not any(r["provider"] == m["provider"] and r["model_id"] == m["model_id"] for r in retired_in_use)
    ]

    # Always record what we saw, even if we choose not to report it.
    core.ai_model_catalog = json.dumps(current, indent=1, sort_keys=True)
    core.ai_model_catalog_checked = now
    core.save(update_fields=["ai_model_catalog", "ai_model_catalog_checked"])

    summary_tail = (f"{len(registered)} registered for use" if registered else "")
    if provider_errors:
        summary_tail += (", " if summary_tail else "") + f"discovery errors: {json.dumps(provider_errors)[:160]}"

    # A first run has no baseline, so everything would look "new". Record and stop.
    if first_run:
        return (f"baseline recorded: {len(cur_set)} models across {len(current)} provider(s)"
                + (f" - {summary_tail}" if summary_tail else "") + register_note)
    if not (added or removed or retired_in_use):
        return (f"no change ({len(cur_set)} models)" + (f" - {summary_tail}" if summary_tail else "") + register_note)

    payload = {
        "added": [{"provider": p, "model_id": m, "display_name": current[p][m]} for p, m in added],
        "removed": [{"provider": p, "model_id": m} for p, m in removed],
        "retired_in_use": retired_in_use,
        "registered": registered,
        "stale_runtime": stale_runtime,
        "totals": {p: len(mids) for p, mids in current.items()},
        "checked_at": now.isoformat(),
    }
    if not (core.ai_helpdesk_code or "").strip():
        return (f"changed but no helpdesk configured: +{len(added)} -{len(removed)} "
                f"retired_in_use={len(retired_in_use)}")
    try:
        rr = _requests.post(
            f"{bridge}/pi/helpdesk-op",
            json={
                "operation": "report_model_changes",
                "args": payload,
                "helpdesk_api": {
                    "base_url": core.ai_helpdesk_api_base_url or "",
                    "api_key": core.ai_helpdesk_api_key or "",
                },
                "helpdesk_code": core.ai_helpdesk_code or "",
            },
            timeout=(10, 120),
        )
        out = rr.json()
    except Exception as e:
        return f"diff found but reporting failed: {e}"
    if out.get("error"):
        return f"diff found, helpdesk reporting error: {str(out['error'])[:200]}"
    return (f"+{len(added)} new, -{len(removed)} gone, {len(retired_in_use)} configured-but-retired, "
            f"{len(registered)} registered for use -> reported: {str(out.get('result'))[:160]}"
            + register_note)


# ---------------------------------------------------------------------------
# SCHEDULED AI RUNTIME UPDATE
#
# Upgrading the AI runtime (the npm package the bridge embeds) restarts the bridge.
# That drops live chats and in-flight background runs, and a runtime whose API has
# drifted can break every AI surface at once. So this task is deliberately timid:
#
#   1. WINDOW    - only inside the operator's chosen time window, on chosen days.
#   2. QUIESCENCE- only when nothing is running (live chats, headless runs, mining,
#                  triage). Otherwise it waits and re-checks until the window ends.
#   3. PROBE     - the new version is installed, then a compatibility probe asserts the
#                  runtime still exports everything the bridge imports and can still
#                  build a model registry. A failed probe is ROLLED BACK, not shipped.
#   4. VERIFY    - after the restart the bridge must come back healthy on the new
#                  version, or it is rolled back and restarted again.
#
# Every outcome is recorded on CoreSettings and reported through the deployment's own
# helpdesk code (same pattern as the model catalog: this task decides nothing about
# what the ticket says).
# ---------------------------------------------------------------------------
BRIDGE_DIR = "/opt/pi-trmm-bridge"
RUNTIME_PKG = "@earendil-works/pi-coding-agent"
NODE_BIN_DIR = "/home/tactical/.local/share/pi-node/node-v22.22.3-linux-x64/bin"

# The bridge speaks to the runtime through ONE compatibility module (src/pi-runtime.js),
# which supports both generations of the runtime API. So the pre-flight check is
# behavioural, not a list of export names: "using the bridge's own adapter, can this
# version build a runtime, apply a key, list models and resolve one?" An export list goes
# stale the moment the vendor renames something; this does not.
RUNTIME_PROBE_JS = (
    "const { piSelfTest, piGeneration } = await import('/opt/pi-trmm-bridge/src/pi-runtime.js');"
    "const out = await piSelfTest({ anthropic: 'probe-placeholder-key' });"
    "out.generation = await piGeneration();"
    "console.log(JSON.stringify(out));"
)


def _runtime_bridge_get(path, timeout=10):
    import requests as _requests

    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    try:
        return _requests.get(f"{bridge}{path}", timeout=timeout).json()
    except Exception as e:
        return {"error": str(e)}


def _runtime_installed_version():
    data = _runtime_bridge_get("/pi/version")
    return data.get("pi_version"), data.get("error")


def _runtime_latest_version(target):
    """Ask the npm registry. A pinned target is returned as-is (still verified on install)."""
    import requests as _requests

    target = (target or "latest").strip()
    if target and target != "latest":
        return target, None
    try:
        r = _requests.get(f"https://registry.npmjs.org/{RUNTIME_PKG}/latest", timeout=20)
        return (r.json() or {}).get("version"), None
    except Exception as e:
        return None, str(e)


def _runtime_busy():
    """Everything that a restart would interrupt. Returns (busy, detail)."""
    from core.models import AITaskRun, AITicketState

    detail = {}
    b = _runtime_bridge_get("/pi/busy")
    if b.get("error"):
        # Cannot prove it is idle => treat as busy. Never restart on a guess.
        return True, {"bridge": f"unreachable: {b['error'][:120]}"}
    detail.update({k: b.get(k) for k in ("active_runs", "active_sessions", "mining")})
    running_tasks = AITaskRun.objects.filter(status="running").count()
    triaging = AITicketState.objects.filter(status="triaging").count()
    detail["running_task_runs"] = running_tasks
    detail["triaging_tickets"] = triaging
    busy = bool(b.get("busy")) or running_tasks > 0 or triaging > 0
    return busy, detail


def _runtime_probe(dirpath):
    """Ask the bridge's own compatibility adapter whether this installed version works."""
    import json as _json
    import os as _os
    import subprocess

    pkg_entry = f"{dirpath}/node_modules/{RUNTIME_PKG}/dist/index.js"
    if not _os.path.exists(pkg_entry):
        return {"ok": False, "error": f"runtime entry point missing: {pkg_entry}"}
    env = dict(_os.environ, PI_PKG=pkg_entry)
    try:
        out = subprocess.run(
            [f"{NODE_BIN_DIR}/node", "--input-type=module", "-e", RUNTIME_PROBE_JS],
            capture_output=True, text=True, timeout=180, cwd=dirpath, env=env,
        )
        lines = [ln for ln in (out.stdout or "").strip().splitlines() if ln.startswith("{")]
        if not lines:
            return {"ok": False, "error": ((out.stderr or "no output").strip())[-300:]}
        return _json.loads(lines[-1])
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


def _runtime_restart_and_verify(expect_version):
    """Ask the bridge to exit (systemd Restart=always brings it back), then verify."""
    import time

    import requests as _requests

    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    try:
        _requests.post(f"{bridge}/pi/restart", json={"force": False}, timeout=15)
    except Exception:
        pass  # the process exits mid-response; a dropped connection is expected
    for _ in range(40):  # up to ~80s
        time.sleep(2)
        data = _runtime_bridge_get("/pi/version", timeout=5)
        if data.get("pi_version"):
            if not expect_version or data["pi_version"] == expect_version:
                return True, data["pi_version"]
            return False, data["pi_version"]
    return False, None


@app.task
def run_ai_runtime_update(force=False):
    """Beat task (every 5 min). Does nothing unless it is inside the window, the system
    is idle, and a newer version actually exists. force=True skips only the window."""
    import json
    import os
    import shutil
    import subprocess
    from datetime import timedelta

    from django.utils import timezone as djangotime

    core = get_core_settings()
    if not core.ai_module_enabled:
        return "ai module disabled"
    if not (force or core.ai_runtime_update_enabled):
        return "runtime update disabled"

    now = djangotime.localtime()

    def _finish(result, version=None):
        core.ai_runtime_update_last_run = djangotime.now()
        core.ai_runtime_update_last_result = result[:2000]
        fields = ["ai_runtime_update_last_run", "ai_runtime_update_last_result"]
        if version:
            core.ai_runtime_update_last_version = version[:32]
            fields.append("ai_runtime_update_last_version")
        core.save(update_fields=fields)
        return result

    # ---- 1. WINDOW ----------------------------------------------------------
    if not force:
        raw = (core.ai_runtime_update_time or "03:30").strip()
        try:
            hh, mm = [int(x) for x in raw.split(":")[:2]]
        except Exception:
            return "invalid update time - expected HH:MM"
        days = [d.strip() for d in (core.ai_runtime_update_days or "").split(",") if d.strip()]
        if days and str(now.weekday()) not in days:
            return "not a scheduled day"
        start = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        wait_min = max(5, core.ai_runtime_update_max_wait_minutes or 180)
        end = start + timedelta(minutes=wait_min)
        if not (start <= now <= end):
            return "outside update window"
        # Already ran (or gave up) in this window? Then stop - one attempt per window.
        last = core.ai_runtime_update_last_run
        if last and djangotime.localtime(last) >= start:
            return "already handled this window"

    # ---- 2. IS THERE ANYTHING TO DO? ---------------------------------------
    installed, verr = _runtime_installed_version()
    if verr or not installed:
        return _finish(f"cannot read installed version: {verr or 'unknown'}")
    target, terr = _runtime_latest_version(core.ai_runtime_update_target)
    if not target:
        return _finish(f"cannot resolve target version: {terr or 'unknown'}")
    if installed == target:
        return _finish(f"up to date ({installed})", version=installed)
    # A version that already failed the probe on this deployment is not retried, so an
    # unattended window cannot churn (install -> fail -> roll back) night after night.
    # It unblocks by itself the moment the provider ships something newer.
    if target and target == (core.ai_runtime_update_blocked_version or ""):
        return _finish(
            f"holding at {installed} - {target} previously failed the compatibility probe "
            f"here; waiting for a newer release"
        )

    # ---- 3. QUIESCENCE ------------------------------------------------------
    busy, detail = _runtime_busy()
    if busy:
        # Deliberately does NOT record last_run: the next tick (still inside the window)
        # tries again, so the update waits for work to finish instead of interrupting it.
        return f"deferred - system busy: {json.dumps(detail)[:300]}"

    # ---- 4. STAGED INSTALL + PROBE -----------------------------------------
    pkg_root = f"{BRIDGE_DIR}/node_modules/{RUNTIME_PKG}"
    backup = f"{BRIDGE_DIR}/.runtime-backup-{installed}"
    try:
        if os.path.exists(backup):
            shutil.rmtree(backup, ignore_errors=True)
        shutil.copytree(pkg_root, backup, symlinks=True)
    except Exception as e:
        return _finish(f"aborted - could not back up the current runtime: {str(e)[:200]}")

    env = dict(os.environ, PATH=f"{NODE_BIN_DIR}:{os.environ.get('PATH', '')}")
    try:
        inst = subprocess.run(
            [f"{NODE_BIN_DIR}/npm", "install", f"{RUNTIME_PKG}@{target}",
             "--no-audit", "--no-fund", "--loglevel=error"],
            cwd=BRIDGE_DIR, capture_output=True, text=True, timeout=900, env=env,
        )
    except Exception as e:
        shutil.rmtree(backup, ignore_errors=True)
        return _finish(f"install failed to start: {str(e)[:200]}")

    def _rollback(reason):
        try:
            shutil.rmtree(pkg_root, ignore_errors=True)
            shutil.copytree(backup, pkg_root, symlinks=True)
        except Exception as e:
            return _finish(f"CRITICAL: rollback failed after {reason}: {str(e)[:200]} - "
                           f"backup kept at {backup}")
        ok, ver = _runtime_restart_and_verify(installed)
        shutil.rmtree(backup, ignore_errors=True)
        return _finish(f"update to {target} rolled back ({reason}); "
                       f"restored {installed}, bridge healthy={ok} version={ver}")

    if inst.returncode != 0:
        return _rollback(f"npm install failed: {(inst.stderr or inst.stdout or '')[-300:]}")

    probe = _runtime_probe(BRIDGE_DIR)
    if not probe.get("ok"):
        why = probe.get("error") or f"adapter self-test failed: {json.dumps(probe)[:300]}"
        core.ai_runtime_update_blocked_version = target[:32]
        core.save(update_fields=["ai_runtime_update_blocked_version"])
        return _rollback(f"incompatible with this deployment: {why}")

    # ---- 5. RESTART + VERIFY ------------------------------------------------
    ok, ver = _runtime_restart_and_verify(target)
    if not ok:
        return _rollback(f"bridge did not come back healthy on {target} (saw {ver})")
    shutil.rmtree(backup, ignore_errors=True)
    if core.ai_runtime_update_blocked_version:
        core.ai_runtime_update_blocked_version = ""
        core.save(update_fields=["ai_runtime_update_blocked_version"])
    result = (f"updated {installed} -> {target} "
              f"(runtime API: {probe.get('generation')}, {probe.get('models')} models loadable)")

    # Report it the same way everything else is reported: the deployment's own code.
    if (core.ai_helpdesk_code or "").strip():
        import requests as _requests

        bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
        body = (
            f"<div style='font-family:Segoe UI,Arial,sans-serif;font-size:13px'>"
            f"<b>AI runtime updated</b><br/>Version {installed} &rarr; <b>{target}</b><br/>"
            f"Compatibility probe passed ({probe.get('models')} models loadable, "
            f"runtime API '{probe.get('generation')}'). "
            f"The bridge was restarted while idle; no chats or background runs were interrupted."
            f"</div>"
        )
        try:
            _requests.post(
                f"{bridge}/pi/helpdesk-op",
                json={
                    "operation": "create_ticket",
                    "args": {"partner_id": 1, "team_id": 3,
                             "subject": f"[Pi.dev AI] Runtime updated to {target}",
                             "body": body,
                             "dedup_key": f"pi-runtime-update-{target}"},
                    "helpdesk_api": {"base_url": core.ai_helpdesk_api_base_url or "",
                                     "api_key": core.ai_helpdesk_api_key or ""},
                    "helpdesk_code": core.ai_helpdesk_code or "",
                },
                timeout=(10, 60),
            )
        except Exception as e:
            result += f" (reporting failed: {str(e)[:120]})"

    # A new runtime usually ships a new bundled model list - re-read the catalog now so
    # additions/retirements are reported immediately rather than up to a day later.
    try:
        refresh_ai_model_catalog(force=True)
    except Exception:
        pass
    return _finish(result, version=target)


# ---------------------------------------------------------------------------
# DAILY TICKET ACTIVITY REPORT
#
# One email a day answering "what happened on the helpdesk?" - for EVERYONE, not just
# the AI: staff replies and closures, customer replies, and the AI's own actions, with a
# direct link per ticket. Data gathering lives in the deployment's helpdesk code
# (`daily_activity`), so this task only formats and sends - nothing here knows what a
# ticket system looks like.
# ---------------------------------------------------------------------------
# --- Handling-time estimation -------------------------------------------------------
# There are no timesheets on these tickets (the fields exist and are all zero), so time
# is DERIVED FROM THE ACTIVITY LOG and clearly labelled as an estimate:
#
#   1. take every timestamped action by that actor on that ticket
#   2. group them into work SESSIONS (a gap longer than `gap` starts a new session)
#   3. session minutes = elapsed span + `per_msg` per action, with a floor and a cap,
#      so one message is not free and a thread spanning hours is not eight hours of work
#   4. multiply by a bounded COMPLEXITY factor from real signals (how many actions, how
#      many distinct participants, whether a customer was in the loop)
#
# The cap is what stops this becoming fiction: a long quiet gap is not work.
def _dr_parse_dt(v):
    from datetime import datetime

    s = str(v or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(s[:26], fmt)
        except Exception:
            continue
    return None


def _dr_sessions(times, gap_min):
    """Group sorted datetimes into [(start, end, count)] sessions."""
    out = []
    for t in sorted([x for x in times if x]):
        if out and (t - out[-1][1]).total_seconds() <= gap_min * 60:
            out[-1] = (out[-1][0], t, out[-1][2] + 1)
        else:
            out.append((t, t, 1))
    return out


def _dr_session_minutes(sessions, cfg):
    total = 0.0
    for start, end, count in sessions:
        span = (end - start).total_seconds() / 60.0
        mins = span + cfg["per_msg"] * count
        mins = max(cfg["min_session"], min(cfg["max_session"], mins))
        total += mins
    return total


def _dr_complexity(events, participants):
    """Bounded 1.0-1.5, from evidence only. Deliberately conservative."""
    n = len(events)
    f = 1.0
    if n >= 4:
        f += 0.1
    if n >= 8:
        f += 0.1
    if participants >= 3:
        f += 0.1
    if any(e.get("kind") == "customer" for e in events):
        f += 0.1   # a human conversation costs more than a one-way note
    if any(not e.get("note") and e.get("kind") == "staff" for e in events):
        f += 0.1   # a tech wrote to the customer: drafting, not just logging
    return min(1.5, round(f, 2))


def _dr_classify(t):
    """Ticket class for baseline comparison, from the subject/team - no AI state needed."""
    subj = (t.get("subject") or "").strip().lower()
    if subj.startswith("[success]") or "backup successful" in subj or "backup completed" in subj:
        return "alert_clean"
    if subj.startswith("[alert]") or subj.startswith("[warning]") or subj.startswith("vzdump") \
            or subj.startswith("zfs") or subj.startswith("backup status") or "[security audit]" in subj:
        return "alert_actionable"
    if (t.get("team") or "").lower() == "alerts":
        return "alert_actionable"
    if not subj:
        return "unknown"
    return "regular"


def _dr_estimate(tickets, cfg):
    """Annotate each ticket with per-actor time, complexity and totals. Returns per-actor rollup."""
    actors = {}
    for t in tickets:
        events = t.get("events") or []
        by_actor = {}
        for e in events:
            if e.get("kind") not in ("staff", "ai"):
                continue      # customer time is not tech time
            by_actor.setdefault((e.get("actor"), e.get("kind")), []).append(_dr_parse_dt(e.get("at")))
        participants = len({e.get("actor") for e in events})
        cx = _dr_complexity(events, participants)
        t["complexity"] = cx
        t["human_minutes"] = 0.0
        t["ai_minutes"] = 0.0
        t["actor_minutes"] = {}
        for (actor, kind), times in by_actor.items():
            sess = _dr_sessions(times, cfg["gap"])
            mins = _dr_session_minutes(sess, cfg) * cx
            t["actor_minutes"][actor] = round(mins, 1)
            if kind == "ai":
                t["ai_minutes"] += mins
            else:
                t["human_minutes"] += mins
            a = actors.setdefault(actor, {"name": actor, "kind": kind, "minutes": 0.0, "sessions": 0,
                                          "tickets": set(), "closed": 0, "companies": set(),
                                          "first": None, "last": None, "classes": {}})
            a["minutes"] += mins
            a["sessions"] += len(sess)
            a["tickets"].add(t.get("ref"))
            if t.get("company"):
                a["companies"].add(t["company"])
            cls = _dr_classify(t)
            a["classes"][cls] = a["classes"].get(cls, 0) + 1
            for st, en, _c in sess:
                if a["first"] is None or st < a["first"]:
                    a["first"] = st
                if a["last"] is None or en > a["last"]:
                    a["last"] = en
            if t.get("terminal"):
                a["closed"] += 1
        t["human_minutes"] = round(t["human_minutes"], 1)
        t["ai_minutes"] = round(t["ai_minutes"], 1)
        t["class"] = _dr_classify(t)
    return actors


def _dr_baselines(baseline, cfg, fallback):
    """Median HUMAN minutes per ticket class, learned from this desk's own closed tickets."""
    import statistics

    buckets = {}
    for b in baseline or []:
        evs = b.get("staff_events") or []
        if not evs:
            continue        # no human action recorded: tells us nothing about human effort
        times = [_dr_parse_dt(e.get("at")) for e in evs]
        mins = _dr_session_minutes(_dr_sessions(times, cfg["gap"]), cfg)
        cls = _dr_classify({"subject": b.get("subject"), "team": b.get("team")})
        buckets.setdefault(cls, []).append(mins)
    out, sample = {}, {}
    for cls, vals in buckets.items():
        out[cls] = round(statistics.median(vals), 1)
        sample[cls] = len(vals)
    for cls, mins in (fallback or {}).items():
        if cls not in out:
            out[cls] = float(mins)
            sample[cls] = 0
    return out, sample


def _dr_esc(v):
    return (
        str("" if v is None else v)
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _dr_when(v):
    # "2026-07-26 16:47:46" -> "07-26 16:47"
    s = str(v or "")
    return s[5:16] if len(s) >= 16 else s


DR_MAX_ROWS = 60          # beyond this an email client starts clipping the message


def _dr_ticket_table(title, rows, note="", limit=DR_MAX_ROWS):
    if not rows:
        return ""
    shown, hidden = rows[:limit], max(0, len(rows) - limit)
    head = ["Ticket", "Subject", "Company", "Team", "Stage", "Assigned", "Activity", "Msgs", "Last touch", "AI"]
    out = [
        f'<h3 style="font-family:Segoe UI,Arial,sans-serif;font-size:15px;color:#1a3c6e;margin:22px 0 4px">'
        f"{_dr_esc(title)} <span style='color:#888;font-weight:normal'>({len(rows)})</span></h3>"
    ]
    if note:
        out.append(f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:12px;color:#777;margin-bottom:6px">{_dr_esc(note)}</div>')
    out.append('<table cellspacing="0" cellpadding="6" style="border-collapse:collapse;width:100%;font-family:Segoe UI,Arial,sans-serif;font-size:12.5px">')
    out.append("<tr>" + "".join(
        f'<th style="background:#1a3c6e;color:#fff;text-align:left;padding:6px">{h}</th>'
        for h in head) + "</tr>")
    for i, t in enumerate(shown):
        bg = "#ffffff" if i % 2 == 0 else "#f7f9fc"
        td = f'style="border:1px solid #d8dee7;padding:6px;background:{bg}"'
        who = t.get("last_author") or t.get("last_touched_by") or ""
        kind = t.get("last_author_kind") or ""
        kind_col = {"ai": "#0b5cad", "staff": "#166534", "customer": "#92400e"}.get(kind, "#444")
        out.append(
            "<tr>"
            f'<td {td}><a href="{_dr_esc(t.get("url"))}" style="color:#0b5cad;font-weight:600;text-decoration:none">{_dr_esc(t.get("ref"))}</a></td>'
            f'<td {td}>{_dr_esc((t.get("subject") or "")[:70])}</td>'
            f'<td {td}>{_dr_esc((t.get("company") or "")[:28])}</td>'
            f'<td {td}>{_dr_esc(t.get("team"))}</td>'
            f'<td {td}>{_dr_esc(t.get("stage"))}</td>'
            f'<td {td}>{_dr_esc(t.get("assignee") or "—")}</td>'
            f'<td {td}>{_dr_esc(_dr_when(t.get("last_activity")))}</td>'
            f'<td {td} align="center">{int(t.get("msgs") or 0)}</td>'
            f'<td {td}><span style="color:{kind_col}">{_dr_esc(who)}</span></td>'
            f'<td {td} align="center">{"yes" if t.get("ai_touched") else "—"}</td>'
            "</tr>"
        )
    out.append("</table>")
    if hidden:
        out.append('<div style="font-family:Segoe UI,Arial,sans-serif;font-size:11.5px;color:#888;margin-top:3px">'
                   f"+ {hidden} more not listed (newest {len(shown)} shown) &mdash; the counters above include all of them.</div>")
    return "".join(out)


DEFAULT_REPORT_PROMPT = (
    "You are the service-desk manager writing the EXECUTIVE SUMMARY at the top of a helpdesk "
    "report for the owner of an MSP.\n\n"
    "You are given figures already computed from the ticket system's activity log. TREAT THEM AS "
    "FACT: never invent, recompute or contradict a number. Your job is judgement, not arithmetic.\n\n"
    "OUTPUT EXACTLY THIS STRUCTURE - four sections, in this order, with these exact headings:\n\n"
    "<h3>Executive Summary</h3>\n"
    "<p>Two or three sentences: volume, what closed, whether the desk kept pace, where the work "
    "actually went, and what share the AI carried.</p>\n"
    "<h3>How The Techs Are Handling Tickets</h3>\n"
    "<ul>\n"
    "<li><b>Name</b> &mdash; one tight assessment per person: load carried, closure rate, "
    "responsiveness, reply quality, and a fair read on anything that looks light or slow. Cite "
    "ticket refs as evidence.</li>\n"
    "</ul>\n"
    "<h3>Things To Watch</h3>\n"
    "<ul>\n"
    "<li>One issue per bullet, most serious first. Cite the ticket refs.</li>\n"
    "</ul>\n"
    "<h3>What I Would Do Next</h3>\n"
    "<ol>\n"
    "<li>Concrete action, most valuable first. Three at most.</li>\n"
    "</ol>\n\n"
    "HARD FORMATTING RULES:\n"
    "- ONE <li> per technician in section 2. Never write the people as a paragraph or run them "
    "together. Start each with <b>Their Name</b> followed by an em dash.\n"
    "- Sections 2, 3 and 4 are ALWAYS lists (<ul>, <ul>, <ol>). Only section 1 is a <p>.\n"
    "- Keep each bullet to 1-3 sentences. No bullet longer than about 45 words.\n"
    "- Write ticket references in full as TICKET/12345.\n"
    "- Return a clean HTML fragment only: no <html>/<head>/<body>, no markdown, no code fences, "
    "no inline styles. Nothing before the first <h3> and nothing after the last </ol>.\n\n"
    "WHAT TO COVER:\n"
    "- Section 2: name every person in the data. Say who is carrying real load and handling it "
    "well and why (throughput, closure rate, responsiveness, consistency, taking the hard "
    "categories). Where someone looks light or slow, say so plainly but fairly and note the "
    "innocent explanations (part-time, escalations only, work logged outside the ticket).\n"
    "- Section 3: standards and quality. Tickets closed with no reply to the customer, slow first "
    "responses, terse or sloppy replies, typos, tickets unassigned or ageing, anything closed "
    "suspiciously fast, uneven practice between techs. Use the reply excerpts to comment on tone "
    "and professionalism only where they show something real.\n\n"
    "STYLE: British English, direct, specific, no filler, no praise for its own sake. If the "
    "evidence is thin, say so rather than guessing. Time figures are ESTIMATED from ticket "
    "activity and cannot see phone calls or remote sessions, so never accuse anyone of not "
    "working on the basis of low logged time. Under 600 words total."
)


# The model is asked for a bare fragment; we own the presentation so the summary looks
# identical every time regardless of how it chose to mark things up.
def _dr_normalise_summary(html):
    import re

    t = (html or "").strip()
    if t.startswith("```"):
        parts = t.split("```")
        t = parts[1] if len(parts) > 1 else t
        t = re.sub(r"^\s*html\s*", "", t, flags=re.I).strip()
    t = re.sub(r"</?(html|head|body)[^>]*>", "", t, flags=re.I)
    t = re.sub(r"<h[124-6]([^>]*)>", r"<h3\1>", t, flags=re.I)
    t = re.sub(r"</h[124-6]>", "</h3>", t, flags=re.I)
    t = t.replace("<strong>", "<b>").replace("</strong>", "</b>")
    t = t.replace("<em>", "<i>").replace("</em>", "</i>")
    # strip any styles the model added, then apply ours
    t = re.sub(r'\s+style="[^"]*"', "", t)
    t = t.replace("<h3>", '<h3 style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#1a3c6e;'
                          'margin:16px 0 6px;padding-bottom:3px;border-bottom:1px solid #e3e8ef">')
    t = t.replace("<p>", '<p style="font-family:Segoe UI,Arial,sans-serif;font-size:13.5px;line-height:1.6;'
                         'color:#1f2937;margin:0 0 10px">')
    t = t.replace("<ul>", '<ul style="margin:0 0 12px;padding-left:20px">')
    t = t.replace("<ol>", '<ol style="margin:0 0 12px;padding-left:22px">')
    t = t.replace("<li>", '<li style="font-family:Segoe UI,Arial,sans-serif;font-size:13.5px;line-height:1.55;'
                          'color:#1f2937;margin:0 0 7px">')
    return t.strip()


def _dr_quality(tickets, actors):
    """Deterministic standards signals per person. Code counts; the model interprets."""
    import statistics

    per = {}
    for t in tickets:
        for actor in (t.get("actor_minutes") or {}):
            a = per.setdefault(actor, {"tickets": 0, "closed": 0, "closed_no_reply": 0,
                                       "replies": 0, "reply_chars": [], "first_resp": [],
                                       "fast_closes": 0, "stale_open": 0})
            a["tickets"] += 1
            if t.get("terminal"):
                a["closed"] += 1
                if t.get("closed_without_reply"):
                    a["closed_no_reply"] += 1
                # closed inside 5 minutes of the last inbound activity is worth a look
                if (t.get("human_minutes") or 0) <= 5 and (t.get("msgs") or 0) <= 1:
                    a["fast_closes"] += 1
            else:
                a["stale_open"] += 1
            if t.get("staff_replies"):
                a["replies"] += t["staff_replies"]
                if t.get("staff_reply_avg_chars"):
                    a["reply_chars"].append(t["staff_reply_avg_chars"])
            if t.get("first_response_minutes") is not None:
                a["first_resp"].append(t["first_response_minutes"])
    out = {}
    for actor, a in per.items():
        out[actor] = {
            "tickets": a["tickets"], "closed": a["closed"],
            "closed_without_reply": a["closed_no_reply"],
            "replies": a["replies"],
            "avg_reply_chars": int(statistics.mean(a["reply_chars"])) if a["reply_chars"] else 0,
            "median_first_response_min": int(statistics.median(a["first_resp"])) if a["first_resp"] else None,
            "closed_in_under_5_min": a["fast_closes"],
            "still_open": a["stale_open"],
        }
    return out


def _dr_summary_html(data, tickets, actors, quality, value, baselines, sample, cfg, hours, core):
    """Ask the model to interpret the computed figures. Falls back to a plain paragraph -
    a summary failing must never cost us the report."""
    import json as _json

    import requests as _requests

    model = _resolve_ai_model(None)
    if not model:
        return ""
    tot = data.get("totals") or {}
    techs = []
    for a in sorted(actors.values(), key=lambda x: -x["minutes"]):
        q = quality.get(a["name"], {})
        techs.append({
            "name": a["name"], "role": a["kind"],
            "estimated_minutes": int(a["minutes"]),
            "tickets": len(a["tickets"]), "closed": a["closed"], "work_sessions": a["sessions"],
            "avg_minutes_per_ticket": int(a["minutes"] / max(1, len(a["tickets"]))),
            "active_window": (f'{a["first"].strftime("%m-%d %H:%M")} to {a["last"].strftime("%m-%d %H:%M")}'
                              if a["first"] and a["last"] else ""),
            "ticket_mix": a["classes"],
            "companies_touched": len(a["companies"]),
            "median_first_response_min": q.get("median_first_response_min"),
            "customer_replies_written": q.get("replies", 0),
            "avg_reply_length_chars": q.get("avg_reply_chars", 0),
            "closed_without_replying_to_customer": q.get("closed_without_reply", 0),
            "closed_in_under_5_min": q.get("closed_in_under_5_min", 0),
            "still_open_on_their_plate": q.get("still_open", 0),
        })
    stale = sorted([t for t in tickets if not t.get("terminal")],
                   key=lambda t: t.get("last_activity") or "")[:12]
    digest = {
        "window_hours": hours,
        "period": f'{data.get("since")} to now',
        "scope": data.get("scope"),
        "totals": tot,
        "time": {
            "tech_minutes_on_closed": int(value["human_total"]),
            "ai_minutes_on_closed": int(value["ai_total"]),
            "human_minutes_saved_by_ai": int(value["saved"]),
            "closed_by_ai_alone": value["ai_only"],
            "closed_by_ai_then_human": value["ai_assisted"],
        },
        "how_time_is_estimated": (
            f"grouped activity into sessions (gap>{cfg['gap']}m), {cfg['per_msg']}m per action, "
            f"floor {cfg['min_session']}m, cap {cfg['max_session']}m, complexity x1.0-1.5; "
            "cannot see phone calls or remote sessions"
        ),
        "human_baseline_minutes_by_type": {k: {"median": v, "sample": sample.get(k, 0)} for k, v in baselines.items()},
        "people": techs,
        "oldest_open_tickets": [
            {"ref": t.get("ref"), "subject": (t.get("subject") or "")[:70], "company": t.get("company"),
             "assignee": t.get("assignee") or "UNASSIGNED", "stage": t.get("stage"),
             "last_activity": t.get("last_activity")} for t in stale
        ],
        "tech_reply_excerpts_for_tone_review": (data.get("reply_samples") or [])[:25],
    }
    prompt = (core.ai_daily_report_prompt or "").strip() or DEFAULT_REPORT_PROMPT
    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    try:
        r = _requests.post(
            f"{bridge}/pi/analyze",
            json={
                "provider": model.provider.name, "api_key": model.provider.api_key,
                "model_id": model.model_id, "thinking_level": model.thinking_level or "medium",
                "system_prompt": prompt,
                "content": "Here are the computed figures for the period:\n\n"
                           + _json.dumps(digest, indent=1, default=str),
            },
            timeout=(10, 420),
        )
        out = r.json()
    except Exception as e:
        out = {"error": str(e)}
    if out.get("error") or not (out.get("text") or "").strip():
        why = str(out.get("error") or "empty response")[:160]
        return (
            '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:12.5px;color:#92400e;'
            'background:#fffbeb;border:1px solid #fcd34d;padding:10px;margin-bottom:14px">'
            f"Executive summary unavailable ({_dr_esc(why)}). The figures below are unaffected.</div>"
        )
    text = _dr_normalise_summary(out.get("text") or "")
    return (
        '<div style="border:1px solid #d8dee7;border-left:4px solid #1a3c6e;background:#fbfcfe;'
        'padding:14px 18px;margin:0 0 18px">'
        f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:13.5px;line-height:1.6;color:#1f2937">{text}</div>'
        '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:10.5px;color:#999;margin-top:10px">'
        "Written by the AI from the computed figures below. Its prompt is editable in "
        "Global Settings &rarr; Pi.dev AI &rarr; Daily Activity Report.</div></div>"
    )


def _dr_fmt_mins(m):
    m = int(round(m or 0))
    if m < 60:
        return f"{m}m"
    return f"{m // 60}h {m % 60:02d}m"


def _dr_actor_table(actors, tickets, quality=None):
    quality = quality or {}
    if not actors:
        return ""
    rows = sorted(actors.values(), key=lambda a: a["minutes"], reverse=True)
    h = ['<h3 style="font-family:Segoe UI,Arial,sans-serif;font-size:15px;color:#1a3c6e;margin:24px 0 4px">'
         "Who did what &mdash; and how long it took</h3>",
         '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:12px;color:#777;margin-bottom:6px">'
         "Time is estimated from the activity log (work sessions &times; complexity), not from timesheets.</div>",
         '<table cellspacing="0" cellpadding="6" style="border-collapse:collapse;font-family:Segoe UI,Arial,sans-serif;font-size:12.5px;width:100%">']
    head = ["Who", "Role", "Est. time", "Tickets", "Closed", "Sessions", "Avg/ticket",
            "Replies", "Avg reply", "1st resp", "Closed w/o reply", "Mix"]
    h.append("<tr>" + "".join(
        f'<th style="background:#1a3c6e;color:#fff;text-align:left;padding:6px">{c}</th>'
        for c in head) + "</tr>")
    for i, a in enumerate(rows[:30]):
        bg = "#ffffff" if i % 2 == 0 else "#f7f9fc"
        td = f'style="border:1px solid #d8dee7;padding:6px;background:{bg}"'
        n = len(a["tickets"]) or 1
        window = ""
        if a["first"] and a["last"]:
            window = f'{a["first"].strftime("%H:%M")}&ndash;{a["last"].strftime("%H:%M")}'
        mix = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in sorted(a["classes"].items(), key=lambda x: -x[1]))
        role = {"ai": "AI", "staff": "tech"}.get(a["kind"], a["kind"])
        colour = "#0b5cad" if a["kind"] == "ai" else "#166534"
        q = quality.get(a["name"], {})
        fr = q.get("median_first_response_min")
        nore = q.get("closed_without_reply", 0)
        h.append(
            "<tr>"
            f'<td {td}><b style="color:{colour}">{_dr_esc(a["name"])}</b></td>'
            f'<td {td}>{role}</td>'
            f'<td {td}><b>{_dr_fmt_mins(a["minutes"])}</b></td>'
            f'<td {td} align="center">{len(a["tickets"])}</td>'
            f'<td {td} align="center">{a["closed"]}</td>'
            f'<td {td} align="center">{a["sessions"]}</td>'
            f'<td {td} align="center">{_dr_fmt_mins(a["minutes"] / n)}</td>'
            f'<td {td} align="center">{q.get("replies", 0)}</td>'
            f'<td {td} align="center">{q.get("avg_reply_chars", 0) or "—"}</td>'
            f'<td {td} align="center">{_dr_fmt_mins(fr) if fr is not None else "—"}</td>'
            f'<td {td} align="center" style="color:{"#b91c1c" if nore else "#666"}">{nore or "—"}</td>'
            f'<td {td}>{_dr_esc(mix)}</td>'
            "</tr>"
        )
    h.append("</table>")
    return "".join(h)


def _dr_tech_detail(actors, tickets, per_tech=15):
    """Per-tech: exactly which tickets they worked, with links. The 'what are my techs
    doing' view - one block per person, biggest first."""
    techs = sorted([a for a in actors.values() if a["kind"] == "staff"],
                   key=lambda a: a["minutes"], reverse=True)
    if not techs:
        return ""
    by_ref = {t.get("ref"): t for t in tickets}
    h = ['<h3 style="font-family:Segoe UI,Arial,sans-serif;font-size:15px;color:#1a3c6e;margin:24px 0 4px">'
         "Per-technician detail</h3>"]
    for a in techs:
        h.append(
            f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:13px;margin:10px 0 2px">'
            f'<b style="color:#166534">{_dr_esc(a["name"])}</b> &mdash; {_dr_fmt_mins(a["minutes"])} across '
            f'{len(a["tickets"])} ticket(s), {a["closed"]} closed, {a["sessions"]} work session(s)</div>'
        )
        h.append('<table cellspacing="0" cellpadding="5" style="border-collapse:collapse;font-family:Segoe UI,Arial,sans-serif;font-size:12px;width:100%;margin-bottom:6px">')
        refs = sorted(a["tickets"], key=lambda r: (by_ref.get(r, {}).get("last_activity") or ""), reverse=True)
        extra = max(0, len(refs) - per_tech)
        for ref in refs[:per_tech]:
            t = by_ref.get(ref) or {}
            td = 'style="border:1px solid #e3e8ef;padding:5px"'
            h.append(
                "<tr>"
                f'<td {td} width="90"><a href="{_dr_esc(t.get("url"))}" style="color:#0b5cad;font-weight:600;text-decoration:none">{_dr_esc(ref)}</a></td>'
                f'<td {td}>{_dr_esc((t.get("subject") or "")[:62])}</td>'
                f'<td {td} width="150">{_dr_esc((t.get("company") or "")[:24])}</td>'
                f'<td {td} width="90">{_dr_esc(t.get("stage"))}</td>'
                f'<td {td} width="70" align="right"><b>{_dr_fmt_mins((t.get("actor_minutes") or {}).get(a["name"], 0))}</b></td>'
                f'<td {td} width="60" align="center">&times;{t.get("complexity", 1)}</td>'
                f'<td {td} width="80" align="center">{"AI helped" if t.get("ai_touched") else ""}</td>'
                "</tr>"
            )
        if extra:
            h.append(f'<tr><td colspan="7" style="border:1px solid #e3e8ef;padding:5px;color:#888;'
                     f'font-size:11.5px">+ {extra} more ticket(s) for this person</td></tr>')
        h.append("</table>")
    return "".join(h)


def _dr_time_value(tickets, actors, baselines, sample, cfg, hours, row_cap=DR_MAX_ROWS):
    """Bottom-line block: time spent on what closed, and what the AI took off the desk."""
    closed = [t for t in tickets if t.get("terminal")]
    human_total = sum(t.get("human_minutes", 0) for t in closed)
    ai_total = sum(t.get("ai_minutes", 0) for t in closed)
    ai_only = [t for t in closed if t.get("ai_touched") and t.get("human_minutes", 0) <= 0]
    ai_assisted = [t for t in closed if t.get("ai_touched") and t.get("human_minutes", 0) > 0]
    saved_full = sum(baselines.get(t.get("class"), 0) for t in ai_only)
    saved_part = 0.0
    for t in ai_assisted:
        base = baselines.get(t.get("class"), 0)
        saved_part += max(0.0, base - t.get("human_minutes", 0))
    saved = saved_full + saved_part

    def card(label, value, sub="", colour="#1a3c6e"):
        return (
            f'<td style="border:1px solid #d8dee7;padding:12px 14px;background:#f7f9fc;text-align:center">'
            f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:22px;font-weight:700;color:{colour}">{value}</div>'
            f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:11px;color:#666;text-transform:uppercase">{label}</div>'
            f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:10.5px;color:#999">{sub}</div></td>'
        )

    h = ['<h3 style="font-family:Segoe UI,Arial,sans-serif;font-size:15px;color:#1a3c6e;margin:26px 0 4px">'
         f"Time worked on what closed &mdash; and time the AI saved</h3>"]
    h.append('<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;width:100%"><tr>')
    h.append(card("tech time on closed tickets", _dr_fmt_mins(human_total), f"{len(closed)} closed in {hours}h"))
    h.append(card("AI time on those tickets", _dr_fmt_mins(ai_total), "machine time, not billable"))
    h.append(card("human time saved by AI", _dr_fmt_mins(saved), f"{len(ai_only)} solo + {len(ai_assisted)} assisted", "#166534"))
    h.append(card("closed with no human at all", len(ai_only), "AI start to finish", "#0b5cad"))
    h.append("</tr></table>")

    # Show the baselines the saving is measured against - the number is only as good as this.
    if baselines:
        h.append('<div style="font-family:Segoe UI,Arial,sans-serif;font-size:12px;color:#555;margin-top:8px">'
                 "<b>Measured against this desk&rsquo;s own history</b> (median human handling time per ticket type, "
                 f"learned from the last {cfg['baseline_days']} days): ")
        parts = []
        for k, v in sorted(baselines.items()):
            n = sample.get(k) or 0
            if n == 0:
                tag = ' <i style="color:#b45309">(no human sample &mdash; configured fallback)</i>'
            elif n < 5:
                tag = f' <i style="color:#b45309">(low confidence, n={n})</i>'
            else:
                tag = f' <span style="color:#999">(n={n})</span>'
            parts.append(f"{k.replace('_', ' ')} <b>{_dr_fmt_mins(v)}</b>{tag}")
        h.append(", ".join(parts))
        h.append("</div>")
        weak = [k for k, v in baselines.items() if (sample.get(k) or 0) < 5]
        if weak:
            h.append('<div style="font-family:Segoe UI,Arial,sans-serif;font-size:11.5px;color:#b45309;margin-top:4px">'
                     f"Note: {', '.join(w.replace('_', ' ') for w in sorted(weak))} has almost no human-handled "
                     "sample left to compare against &mdash; the AI now does nearly all of it, so that saving leans on "
                     "the configured fallback rather than measured history.</div>")

    # The closed tickets themselves, with the time attributed.
    if closed:
        h.append('<table cellspacing="0" cellpadding="6" style="border-collapse:collapse;width:100%;font-family:Segoe UI,Arial,sans-serif;font-size:12.5px;margin-top:12px">')
        head = ["Ticket", "Subject", "Company", "Type", "Who worked it", "Tech time", "AI time", "Cx", "Saved"]
        h.append("<tr>" + "".join(
            f'<th style="background:#1a3c6e;color:#fff;text-align:left;padding:6px">{c}</th>'
            for c in head) + "</tr>")
        closed_sorted = sorted(closed, key=lambda x: x.get("human_minutes", 0), reverse=True)
        closed_hidden = max(0, len(closed_sorted) - row_cap)
        for i, t in enumerate(closed_sorted[:row_cap]):
            bg = "#ffffff" if i % 2 == 0 else "#f7f9fc"
            td = f'style="border:1px solid #d8dee7;padding:6px;background:{bg}"'
            base = baselines.get(t.get("class"), 0)
            sv = base if (t.get("ai_touched") and t.get("human_minutes", 0) <= 0) else (
                max(0.0, base - t.get("human_minutes", 0)) if t.get("ai_touched") else 0)
            who = ", ".join(k for k in (t.get("actor_minutes") or {})) or "&mdash;"
            h.append(
                "<tr>"
                f'<td {td}><a href="{_dr_esc(t.get("url"))}" style="color:#0b5cad;font-weight:600;text-decoration:none">{_dr_esc(t.get("ref"))}</a></td>'
                f'<td {td}>{_dr_esc((t.get("subject") or "")[:56])}</td>'
                f'<td {td}>{_dr_esc((t.get("company") or "")[:22])}</td>'
                f'<td {td}>{_dr_esc((t.get("class") or "").replace("_", " "))}</td>'
                f'<td {td}>{who}</td>'
                f'<td {td} align="right"><b>{_dr_fmt_mins(t.get("human_minutes", 0))}</b></td>'
                f'<td {td} align="right" style="color:#0b5cad">{_dr_fmt_mins(t.get("ai_minutes", 0))}</td>'
                f'<td {td} align="center">&times;{t.get("complexity", 1)}</td>'
                f'<td {td} align="right" style="color:#166534">{_dr_fmt_mins(sv) if sv else ""}</td>'
                "</tr>"
            )
        h.append("</table>")
        if closed_hidden:
            h.append('<div style="font-family:Segoe UI,Arial,sans-serif;font-size:11.5px;color:#888;margin-top:3px">'
                     f"+ {closed_hidden} more closed ticket(s) not listed (highest tech time shown first) &mdash; "
                     "the totals above include every one of them.</div>")
    return "".join(h), {"human_total": human_total, "ai_total": ai_total, "saved": saved,
                        "ai_only": len(ai_only), "ai_assisted": len(ai_assisted)}


def _dr_system_block():
    """State of the AI itself: what it is running, what it is allowed to do, what it knows.
    Included so the daily mail is a full picture, not just a ticket list."""
    import json as _json

    from core.models import AIModel, AIProcedure, AITicketState

    core = get_core_settings()
    rows = []
    ver = _runtime_bridge_get("/pi/version", timeout=5)
    rows.append(("AI runtime", f"{ver.get('pi_version') or 'unreachable'} "
                               f"({ver.get('runtime_generation') or '?'} API), node {ver.get('node_version') or '?'}"))
    rows.append(("Scheduled runtime update",
                 f"{'on' if core.ai_runtime_update_enabled else 'off'} at {core.ai_runtime_update_time}"
                 f" — last: {(core.ai_runtime_update_last_result or 'never')[:90]}"))
    try:
        cat = _json.loads(core.ai_model_catalog or "{}")
        nmod = sum(len(v) for v in cat.values())
    except Exception:
        nmod = 0
    rows.append(("Model catalog", f"{nmod} models tracked, checked "
                                  f"{core.ai_model_catalog_checked.strftime('%m-%d %H:%M') if core.ai_model_catalog_checked else 'never'}"
                                  f"; auto-register {'on' if core.ai_model_autoregister else 'off'}"))
    rows.append(("Models available to techs",
                 ", ".join(f"{m.model_id}{' (default)' if m.is_default else ''}"
                           for m in AIModel.objects.filter(enabled=True)) or "none"))
    rows.append(("Ticket automation",
                 f"{'on' if core.ai_ticket_automation_enabled else 'off'}, act-on-alerts "
                 f"{'on' if core.ai_ticket_act_on_alerts else 'off'}"))
    rows.append(("Alert verifiers",
                 f"{'on' if core.ai_verifiers_enabled else 'off'}"
                 f"{' — DRY RUN (reports, does not act)' if core.ai_verifiers_dry_run else ' — acting'}"))
    rows.append(("Knowledge base",
                 f"{AIProcedure.objects.count()} procedures "
                 f"({AIProcedure.objects.filter(status='approved').count()} approved), "
                 f"mined {core.ai_procedures_last_mined.strftime('%m-%d %H:%M') if core.ai_procedures_last_mined else 'never'}"))
    rows.append(("Awaiting a human decision",
                 f"{AITicketState.objects.filter(status='needs_input').count()} ticket(s) tagged for input"))
    h = ['<h3 style="font-family:Segoe UI,Arial,sans-serif;font-size:15px;color:#1a3c6e;margin:26px 0 4px">'
         "AI system state</h3>",
         '<table cellspacing="0" cellpadding="6" style="border-collapse:collapse;font-family:Segoe UI,Arial,sans-serif;font-size:12.5px;width:100%">']
    for i, (k, v) in enumerate(rows):
        bg = "#ffffff" if i % 2 == 0 else "#f7f9fc"
        h.append(f'<tr><td style="border:1px solid #d8dee7;padding:6px;background:{bg};width:230px;color:#555">{_dr_esc(k)}</td>'
                 f'<td style="border:1px solid #d8dee7;padding:6px;background:{bg}">{_dr_esc(v)}</td></tr>')
    h.append("</table>")
    return "".join(h)


def _dr_render(data, hours, cfg, core=None):
    tot = data.get("totals") or {}
    tickets = data.get("tickets") or []

    # Derive time from the activity log, then learn what a human normally takes.
    actors = _dr_estimate(tickets, cfg)
    baselines, sample = _dr_baselines(data.get("baseline"), cfg, cfg.get("fallback") or {})
    # Long windows would otherwise produce an email the client truncates, which silently
    # hides the tail. Cap the lists instead, and say how many were left out.
    row_cap = DR_MAX_ROWS if hours <= 48 else 15
    per_tech = 15 if hours <= 48 else 5
    value_html, value = _dr_time_value(tickets, actors, baselines, sample, cfg, hours, row_cap)
    quality = _dr_quality(tickets, actors)

    def card(label, value_, colour="#1a3c6e"):
        return (
            f'<td style="border:1px solid #d8dee7;padding:10px 14px;background:#f7f9fc;text-align:center">'
            f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:22px;font-weight:700;color:{colour}">{value_}</div>'
            f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:11px;color:#666;text-transform:uppercase">{label}</div></td>'
        )

    h = ['<div style="max-width:1180px;margin:0 auto;padding:16px;background:#fff">']
    h.append(
        f'<h1 style="font-family:Segoe UI,Arial,sans-serif;font-size:21px;color:#1a3c6e;margin:0 0 2px">'
        f"Helpdesk daily report &mdash; last {hours} hours</h1>"
        f'<div style="font-family:Segoe UI,Arial,sans-serif;font-size:12px;color:#777;margin-bottom:14px">'
        f'{_dr_esc(data.get("since"))} &rarr; now &middot; scope: {_dr_esc(data.get("scope"))} &middot; '
        f"everyone&rsquo;s activity, techs and AI</div>"
    )
    # Executive summary first: the interpretation, before the evidence.
    if core is not None and core.ai_daily_report_ai_summary:
        h.append(_dr_summary_html(data, tickets, actors, quality, value, baselines, sample, cfg, hours, core))

    h.append('<table cellspacing="0" cellpadding="0" style="border-collapse:collapse;width:100%"><tr>')
    h.append(card("touched", tot.get("tickets_with_activity", 0)))
    h.append(card("created", tot.get("created", 0)))
    h.append(card("closed", tot.get("terminal_now", 0), "#166534"))
    h.append(card("still open", tot.get("open_now", 0), "#92400e"))
    h.append(card("unassigned", tot.get("unassigned_open", 0), "#b91c1c"))
    h.append(card("tech time", _dr_fmt_mins(value["human_total"])))
    h.append(card("AI saved", _dr_fmt_mins(value["saved"]), "#166534"))
    h.append(card("no AI involvement", tot.get("untouched_by_ai", 0), "#555"))
    h.append("</tr></table>")

    h.append(_dr_actor_table(actors, tickets, quality))
    h.append(_dr_tech_detail(actors, tickets, per_tech))

    open_rows = [t for t in tickets if not t.get("terminal")]
    no_ai = [t for t in tickets if not t.get("ai_touched")]
    h.append(_dr_ticket_table("Still open", sorted(open_rows, key=lambda t: t.get("last_activity") or "", reverse=True),
                              "Anything with no assignee has nobody on it.", row_cap))
    h.append(_dr_ticket_table("Handled with no AI involvement", no_ai,
                              "Either out of the AI's scope, or a human got there first.", row_cap))
    h.append(value_html)
    h.append(_dr_system_block())
    h.append(
        '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:11px;color:#888;margin-top:24px;'
        'border-top:1px solid #e3e8ef;padding-top:8px">'
        "<b>How time is calculated.</b> These tickets carry no timesheets, so time is <b>estimated from the "
        "activity log</b>: each person&rsquo;s actions on a ticket are grouped into work sessions "
        f"(a gap over {cfg['gap']} min starts a new one), each session counted as its elapsed span plus "
        f"{cfg['per_msg']} min per action, floored at {cfg['min_session']} min and capped at "
        f"{cfg['max_session']} min so idle gaps are never billed, then multiplied by a complexity factor "
        "(1.0&ndash;1.5) from message volume, participants and whether a customer was in the loop. "
        "<b>What it cannot see:</b> work done outside the ticket &mdash; remote sessions, phone calls, "
        "desk visits &mdash; leaves no timestamp here, so tech time is a <b>floor, not a total</b>. Raise "
        "&ldquo;minutes per action&rdquo; in Global Settings if your team&rsquo;s real cost per touch is higher. "
        "<b>AI time saved</b> compares each AI-handled ticket against the median time a human on this desk "
        f"actually spends on that ticket type (last {cfg['baseline_days']} days); where a human still had to "
        "step in, only the difference is credited. Treat these as directional, not invoices. "
        "Every ticket reference links straight to the ticket.</div></div>"
    )
    return "".join(h), value


@app.task
def send_daily_ticket_report(force=False, hours=None, recipients_override=None):
    """Beat task (ticks every 5 min). Sends once per day at the configured time.
    `hours` overrides the window for an ad-hoc run (e.g. a 14-day catch-up report)."""
    import requests as _requests
    from datetime import timedelta

    from django.utils import timezone as djangotime

    core = get_core_settings()
    if not (force or (core.ai_module_enabled and core.ai_daily_report_enabled)):
        return "daily report disabled"
    if not (core.ai_helpdesk_code or "").strip():
        return "no helpdesk integration configured"

    now = djangotime.localtime()
    if not force:
        raw = (core.ai_daily_report_time or "07:00").strip()
        try:
            hh, mm = [int(x) for x in raw.split(":")[:2]]
        except Exception:
            return "invalid report time - expected HH:MM"
        start = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if now < start or now > start + timedelta(hours=2):
            return "outside report window"
        last = core.ai_daily_report_last_run
        if last and djangotime.localtime(last) >= start:
            return "already sent today"

    hours = max(1, int(hours or core.ai_daily_report_hours or 24))
    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")

    def _finish(msg):
        core.ai_daily_report_last_run = djangotime.now()
        core.ai_daily_report_last_result = msg[:1000]
        core.save(update_fields=["ai_daily_report_last_run", "ai_daily_report_last_result"])
        return msg

    try:
        r = _requests.post(
            f"{bridge}/pi/helpdesk-op",
            json={
                "operation": "daily_activity",
                "args": {"hours": hours, "all_teams": bool(core.ai_daily_report_all_teams),
                         "baseline_days": core.ai_report_baseline_days or 14},
                "helpdesk_api": {"base_url": core.ai_helpdesk_api_base_url or "",
                                 "api_key": core.ai_helpdesk_api_key or ""},
                "helpdesk_code": core.ai_helpdesk_code or "",
            },
            timeout=(10, 900),
        )
        payload = r.json()
    except Exception as e:
        return _finish(f"data collection failed: {str(e)[:200]}")
    if payload.get("error"):
        return _finish(f"data collection error: {str(payload['error'])[:200]}")
    data = payload.get("result") or payload
    if not isinstance(data, dict) or "totals" not in data:
        return _finish(f"unexpected data shape from daily_activity: {str(data)[:160]}")

    recipients = [x.strip() for x in (recipients_override or core.ai_daily_report_recipients or "").replace(";", ",").split(",") if x.strip()]
    if not recipients:
        recipients = list(core.email_alert_recipients or [])
    if not recipients:
        return _finish("no recipients configured (set them on the report, or as SMTP alert recipients)")

    tot = data.get("totals") or {}
    import json as _json
    try:
        fallback = _json.loads(core.ai_report_fallback_minutes or "{}")
    except Exception:
        fallback = {}
    cfg = {
        "gap": core.ai_report_session_gap_minutes or 30,
        "per_msg": core.ai_report_minutes_per_message or 4,
        "min_session": core.ai_report_min_session_minutes or 5,
        "max_session": core.ai_report_max_session_minutes or 90,
        "baseline_days": core.ai_report_baseline_days or 14,
        "fallback": fallback,
    }
    html, value = _dr_render(data, hours, cfg, core)
    if data.get("truncated"):
        html = ('<div style="font-family:Segoe UI,Arial,sans-serif;font-size:12.5px;color:#b91c1c;'
                'border:1px solid #b91c1c;background:#fef2f2;padding:8px;margin-bottom:10px">'
                "Row cap reached for this window &mdash; the oldest activity in the period is not "
                "included, so totals below are understated.</div>") + html
    label = "daily report" if hours <= 24 else f"{round(hours / 24)}-day report"
    subject = (
        f"Helpdesk {label} — {tot.get('terminal_now', 0)} closed, "
        f"{_dr_fmt_mins(value['human_total'])} tech time, "
        f"{_dr_fmt_mins(value['saved'])} saved by AI "
        f"({tot.get('open_now', 0)} still open, {tot.get('unassigned_open', 0)} unassigned)"
    )
    text = (
        f"Helpdesk activity, last {hours}h ({data.get('since')} -> now), scope {data.get('scope')}.\n"
        f"Touched {tot.get('tickets_with_activity', 0)} | created {tot.get('created', 0)} | "
        f"closed/cancelled {tot.get('terminal_now', 0)} | still open {tot.get('open_now', 0)} | "
        f"unassigned {tot.get('unassigned_open', 0)}\n"
        f"Customer replies {tot.get('customer_visible', 0)} | internal notes {tot.get('internal_notes', 0)} | "
        f"no AI involvement {tot.get('untouched_by_ai', 0)}\n"
        f"Estimated tech time on closed tickets {_dr_fmt_mins(value['human_total'])}; "
        f"human time saved by AI {_dr_fmt_mins(value['saved'])} "
        f"({value['ai_only']} closed with no human, {value['ai_assisted']} assisted)\n\n"
        "This report is best viewed as HTML (every ticket links straight through).\n"
    )
    msg, ok = core.send_mail(subject=subject, body=text, html_body=html, override_recipients=recipients)
    if not ok:
        return _finish(f"email failed: {str(msg)[:200]}")
    return _finish(
        f"sent to {', '.join(recipients)} — {tot.get('tickets_with_activity', 0)} tickets, "
        f"{len(data.get('actors') or [])} people/systems active, "
        f"{_dr_fmt_mins(value['human_total'])} tech time, {_dr_fmt_mins(value['saved'])} saved by AI"
    )
