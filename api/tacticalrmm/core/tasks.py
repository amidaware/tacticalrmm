import asyncio
import traceback
from contextlib import suppress
from time import sleep
from typing import TYPE_CHECKING, Any

import nats
from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.db.utils import DatabaseError
from django.utils import timezone as djangotime
from packaging import version as pyver

from accounts.models import User
from accounts.utils import is_superuser
from agents.models import Agent
from agents.tasks import clear_faults_task, prune_agent_history
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
from logs.models import PendingAction
from logs.tasks import prune_audit_log, prune_debug_log
from tacticalrmm.celery import app
from tacticalrmm.constants import (
    AGENT_DEFER,
    AGENT_STATUS_ONLINE,
    AGENT_STATUS_OVERDUE,
    RESOLVE_ALERTS_LOCK,
    SYNC_MESH_PERMS_TASK_LOCK,
    SYNC_SCHED_TASK_LOCK,
    AlertSeverity,
    AlertType,
    PAAction,
    PAStatus,
    TaskStatus,
    TaskSyncStatus,
    TaskType,
)
from tacticalrmm.helpers import make_random_password, setup_nats_options
from tacticalrmm.logger import logger
from tacticalrmm.nats_utils import a_nats_cmd
from tacticalrmm.permissions import _has_perm_on_agent
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
            if (
                not agent.is_posix
                and pyver.parse(agent.version) >= pyver.parse("1.6.0")
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


@app.task(bind=True)
def sync_mesh_perms_task(self):
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
                if i.mesh_node_id
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
