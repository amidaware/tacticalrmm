import asyncio
import logging
import re
from collections import Counter
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Union, cast

import msgpack
import nats
import validators
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models
from django.utils import timezone as djangotime
from nats.errors import TimeoutError
from packaging import version as pyver
from packaging.version import Version as LooseVersion

from agents.utils import get_agent_url
from checks.models import CheckResult
from core.models import TZ_CHOICES
from core.utils import _b64_to_hex, get_core_settings, send_command_with_mesh
from logs.models import BaseAuditModel, DebugLog, PendingAction
from tacticalrmm.constants import (
    AGENT_STATUS_OFFLINE,
    AGENT_STATUS_ONLINE,
    AGENT_STATUS_OVERDUE,
    AGENT_TBL_PEND_ACTION_CNT_CACHE_PREFIX,
    ONLINE_AGENTS,
    AgentHistoryType,
    AgentMonType,
    AgentPlat,
    AlertSeverity,
    CheckStatus,
    CheckType,
    CustomFieldType,
    DebugLogType,
    GoArch,
    PAAction,
    PAStatus,
)
from tacticalrmm.helpers import has_script_actions, has_webhook, setup_nats_options
from tacticalrmm.models import PermissionQuerySet

if TYPE_CHECKING:
    from alerts.models import Alert, AlertTemplate
    from automation.models import Policy
    from autotasks.models import AutomatedTask
    from checks.models import Check
    from clients.models import Client
    from winupdate.models import WinUpdatePolicy

# type helpers
Disk = Union[Dict[str, Any], str]

logger = logging.getLogger("trmm")


class Agent(BaseAuditModel):
    class Meta:
        indexes = [
            models.Index(fields=["monitoring_type"]),
        ]

    objects = PermissionQuerySet.as_manager()

    version = models.CharField(default="0.1.0", max_length=255)
    operating_system = models.CharField(null=True, blank=True, max_length=255)
    plat: "AgentPlat" = models.CharField(  # type: ignore
        max_length=255, choices=AgentPlat.choices, default=AgentPlat.WINDOWS
    )
    goarch: "GoArch" = models.CharField(  # type: ignore
        max_length=255, choices=GoArch.choices, null=True, blank=True
    )
    hostname = models.CharField(max_length=255)
    agent_id = models.CharField(max_length=200, unique=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    services = models.JSONField(null=True, blank=True)
    public_ip = models.CharField(null=True, max_length=255)
    total_ram = models.IntegerField(null=True, blank=True)
    disks = models.JSONField(null=True, blank=True)
    boot_time = models.FloatField(null=True, blank=True)
    logged_in_username = models.CharField(null=True, blank=True, max_length=255)
    last_logged_in_user = models.CharField(null=True, blank=True, max_length=255)
    monitoring_type = models.CharField(
        max_length=30, choices=AgentMonType.choices, default=AgentMonType.SERVER
    )
    description = models.CharField(null=True, blank=True, max_length=255)
    mesh_node_id = models.CharField(null=True, blank=True, max_length=255)
    overdue_email_alert = models.BooleanField(default=False)
    overdue_text_alert = models.BooleanField(default=False)
    overdue_dashboard_alert = models.BooleanField(default=False)
    offline_time = models.PositiveIntegerField(default=4)
    overdue_time = models.PositiveIntegerField(default=30)
    check_interval = models.PositiveIntegerField(default=120)
    needs_reboot = models.BooleanField(default=False)
    choco_installed = models.BooleanField(default=False)
    wmi_detail = models.JSONField(null=True, blank=True)
    patches_last_installed = models.DateTimeField(null=True, blank=True)
    time_zone = models.CharField(
        max_length=255, choices=TZ_CHOICES, null=True, blank=True
    )
    maintenance_mode = models.BooleanField(default=False)
    block_policy_inheritance = models.BooleanField(default=False)
    alert_template = models.ForeignKey(
        "alerts.AlertTemplate",
        related_name="agents",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    site = models.ForeignKey(
        "clients.Site",
        related_name="agents",
        on_delete=models.RESTRICT,
    )
    policy = models.ForeignKey(
        "automation.Policy",
        related_name="agents",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self) -> str:
        return self.hostname

    def save(self, *args, **kwargs):
        # prevent recursion since calling set_alert_template() also calls save()
        if not hasattr(self, "_processing_set_alert_template"):
            self._processing_set_alert_template = False

        if self.pk and not self._processing_set_alert_template:
            orig = Agent.objects.get(pk=self.pk)
            mon_type_changed = self.monitoring_type != orig.monitoring_type
            site_changed = self.site_id != orig.site_id
            policy_changed = self.policy != orig.policy
            block_inherit = (
                self.block_policy_inheritance != orig.block_policy_inheritance
            )

            if mon_type_changed or site_changed or policy_changed or block_inherit:
                self._processing_set_alert_template = True
                self.set_alert_template()
                self._processing_set_alert_template = False

        super().save(*args, **kwargs)

    @property
    def client(self) -> "Client":
        return self.site.client

    @property
    def timezone(self) -> str:
        # return the default timezone unless the timezone is explicity set per agent
        if self.time_zone:
            return self.time_zone

        return get_core_settings().default_time_zone

    @property
    def is_posix(self) -> bool:
        return self.plat in {AgentPlat.LINUX, AgentPlat.DARWIN}

    # DEPRECATED, use goarch instead
    @property
    def arch(self) -> Optional[str]:
        if self.is_posix:
            return self.goarch

        if self.operating_system is not None:
            if "64 bit" in self.operating_system or "64bit" in self.operating_system:
                return "64"
            elif "32 bit" in self.operating_system or "32bit" in self.operating_system:
                return "32"
        return None

    def do_update(self, *, token: str = "", force: bool = False) -> str:
        ver = settings.LATEST_AGENT_VER

        if not self.goarch:
            DebugLog.warning(
                agent=self,
                log_type=DebugLogType.AGENT_ISSUES,
                message=f"Unable to determine arch on {self.hostname}({self.agent_id}). Skipping agent update.",
            )
            return "noarch"

        if pyver.parse(self.version) <= pyver.parse("1.3.0"):
            return "not supported"

        url = get_agent_url(goarch=self.goarch, plat=self.plat, token=token)
        bin = f"tacticalagent-v{ver}-{self.plat}-{self.goarch}.exe"

        if not force:
            if self.pendingactions.filter(  # type: ignore
                action_type=PAAction.AGENT_UPDATE, status=PAStatus.PENDING
            ).exists():
                self.pendingactions.filter(  # type: ignore
                    action_type=PAAction.AGENT_UPDATE, status=PAStatus.PENDING
                ).delete()

            PendingAction.objects.create(
                agent=self,
                action_type=PAAction.AGENT_UPDATE,
                details={
                    "url": url,
                    "version": ver,
                    "inno": bin,
                },
            )

        nats_data = {
            "func": "agentupdate",
            "payload": {
                "url": url,
                "version": ver,
                "inno": bin,
            },
        }
        asyncio.run(self.nats_cmd(nats_data, wait=False))
        return "created"

    @property
    def status(self) -> str:
        now = djangotime.now()
        offline = now - djangotime.timedelta(minutes=self.offline_time)
        overdue = now - djangotime.timedelta(minutes=self.overdue_time)

        if self.last_seen is not None:
            if (self.last_seen < offline) and (self.last_seen > overdue):
                return AGENT_STATUS_OFFLINE
            elif (self.last_seen < offline) and (self.last_seen < overdue):
                return AGENT_STATUS_OVERDUE
            else:
                return AGENT_STATUS_ONLINE
        else:
            return AGENT_STATUS_OFFLINE

    @property
    def checks(self) -> Dict[str, Any]:
        total, passing, failing, warning, info = 0, 0, 0, 0, 0

        for check in self.get_checks_with_policies(exclude_overridden=True):
            total += 1
            if (
                not hasattr(check.check_result, "status")
                or isinstance(check.check_result, CheckResult)
                and check.check_result.status == CheckStatus.PASSING
            ):
                passing += 1
            elif (
                isinstance(check.check_result, CheckResult)
                and check.check_result.status == CheckStatus.FAILING
            ):
                alert_severity = (
                    check.check_result.alert_severity
                    if check.check_type
                    in (
                        CheckType.MEMORY,
                        CheckType.CPU_LOAD,
                        CheckType.DISK_SPACE,
                        CheckType.SCRIPT,
                    )
                    else check.alert_severity
                )
                if alert_severity == AlertSeverity.ERROR:
                    failing += 1
                elif alert_severity == AlertSeverity.WARNING:
                    warning += 1
                elif alert_severity == AlertSeverity.INFO:
                    info += 1

        ret = {
            "total": total,
            "passing": passing,
            "failing": failing,
            "warning": warning,
            "info": info,
            "has_failing_checks": failing > 0 or warning > 0,
        }
        return ret

    @property
    def pending_actions_count(self) -> int:
        ret = cache.get(f"{AGENT_TBL_PEND_ACTION_CNT_CACHE_PREFIX}{self.pk}")
        if ret is None:
            ret = self.pendingactions.filter(status=PAStatus.PENDING).count()
            cache.set(f"{AGENT_TBL_PEND_ACTION_CNT_CACHE_PREFIX}{self.pk}", ret, 600)

        return ret

    @property
    def cpu_model(self) -> List[str]:
        if self.is_posix:
            try:
                return cast(List[str], self.wmi_detail["cpus"])
            except:
                return ["unknown cpu model"]

        ret = []
        try:
            cpus = self.wmi_detail["cpu"]
            for cpu in cpus:
                name = [x["Name"] for x in cpu if "Name" in x][0]
                lp, nc = "", ""
                with suppress(Exception):
                    lp = [
                        x["NumberOfLogicalProcessors"]
                        for x in cpu
                        if "NumberOfCores" in x
                    ][0]
                    nc = [x["NumberOfCores"] for x in cpu if "NumberOfCores" in x][0]
                if lp and nc:
                    cpu_string = f"{name}, {nc}C/{lp}T"
                else:
                    cpu_string = name
                ret.append(cpu_string)
            return ret
        except:
            return ["unknown cpu model"]

    @property
    def graphics(self) -> str:
        if self.is_posix:
            try:
                if not self.wmi_detail["gpus"]:
                    return "No graphics cards"

                return ", ".join(self.wmi_detail["gpus"])
            except:
                return "Error getting graphics cards"

        ret, mrda = [], []
        try:
            graphics = self.wmi_detail["graphics"]
            for i in graphics:
                caption = [x["Caption"] for x in i if "Caption" in x][0]
                if "microsoft remote display adapter" in caption.lower():
                    mrda.append("yes")
                    continue

                ret.append([x["Caption"] for x in i if "Caption" in x][0])

            # only return this if no other graphics cards
            if not ret and mrda:
                return "Microsoft Remote Display Adapter"

            return ", ".join(ret)
        except:
            return "Graphics info requires agent v1.4.14"

    @property
    def local_ips(self) -> str:
        if self.is_posix:
            try:
                return ", ".join(self.wmi_detail["local_ips"])
            except:
                return "error getting local ips"

        ret = []
        try:
            ips = self.wmi_detail["network_config"]
        except:
            return "error getting local ips"

        for i in ips:
            try:
                addr = [x["IPAddress"] for x in i if "IPAddress" in x][0]
            except:
                continue

            if addr is None:
                continue

            for ip in addr:
                if validators.ipv4(ip):
                    ret.append(ip)

        if len(ret) == 1:
            return cast(str, ret[0])

        return ", ".join(ret) if ret else "error getting local ips"

    @property
    def make_model(self) -> str:
        if self.is_posix:
            try:
                return cast(str, self.wmi_detail["make_model"])
            except:
                return "error getting make/model"

        with suppress(Exception):
            comp_sys = self.wmi_detail["comp_sys"][0]
            comp_sys_prod = self.wmi_detail["comp_sys_prod"][0]
            make = [x["Vendor"] for x in comp_sys_prod if "Vendor" in x][0]
            model = [x["Model"] for x in comp_sys if "Model" in x][0]

            if "to be filled" in model.lower():
                mobo = self.wmi_detail["base_board"][0]
                make = [x["Manufacturer"] for x in mobo if "Manufacturer" in x][0]
                model = [x["Product"] for x in mobo if "Product" in x][0]

            if make.lower() == "lenovo":
                sysfam = [x["SystemFamily"] for x in comp_sys if "SystemFamily" in x][0]
                if "to be filled" not in sysfam.lower():
                    model = sysfam

            return f"{make} {model}"

        with suppress(Exception):
            comp_sys_prod = self.wmi_detail["comp_sys_prod"][0]
            return cast(str, [x["Version"] for x in comp_sys_prod if "Version" in x][0])

        return "unknown make/model"

    @property
    def physical_disks(self) -> Sequence[Disk]:
        if self.is_posix:
            try:
                return cast(List[Disk], self.wmi_detail["disks"])
            except:
                return ["unknown disk"]

        try:
            disks = self.wmi_detail["disk"]
            ret = []
            for disk in disks:
                interface_type = [
                    x["InterfaceType"] for x in disk if "InterfaceType" in x
                ][0]

                if interface_type == "USB":
                    continue

                model = [x["Caption"] for x in disk if "Caption" in x][0]
                size = [x["Size"] for x in disk if "Size" in x][0]

                size_in_gb = round(int(size) / 1_073_741_824)
                ret.append(f"{model} {size_in_gb:,}GB {interface_type}")

            return ret
        except:
            return ["unknown disk"]

    @property
    def serial_number(self) -> str:
        if self.is_posix:
            try:
                return self.wmi_detail["serialnumber"]
            except:
                return ""

        try:
            return self.wmi_detail["bios"][0][0]["SerialNumber"]
        except:
            return ""

    @property
    def hex_mesh_node_id(self) -> str:
        return _b64_to_hex(self.mesh_node_id)

    @classmethod
    def online_agents(cls, min_version: str = "") -> "List[Agent]":
        if min_version:
            return [
                i
                for i in cls.objects.only(*ONLINE_AGENTS)
                if pyver.parse(i.version) >= pyver.parse(min_version)
                and i.status == AGENT_STATUS_ONLINE
            ]

        return [
            i
            for i in cls.objects.only(*ONLINE_AGENTS)
            if i.status == AGENT_STATUS_ONLINE
        ]

    def is_supported_script(self, platforms: List[str]) -> bool:
        return self.plat.lower() in platforms if platforms else True

    def get_checks_with_policies(
        self, exclude_overridden: bool = False
    ) -> "List[Check]":
        if exclude_overridden:
            checks = (
                list(
                    check
                    for check in self.agentchecks.all()
                    if not check.overridden_by_policy
                )
                + self.get_checks_from_policies()
            )
        else:
            checks = list(self.agentchecks.all()) + self.get_checks_from_policies()
        return self.add_check_results(checks)

    def get_tasks_with_policies(self) -> "List[AutomatedTask]":
        tasks = list(self.autotasks.all()) + self.get_tasks_from_policies()
        return self.add_task_results(tasks)

    def add_task_results(self, tasks: "List[AutomatedTask]") -> "List[AutomatedTask]":
        results = self.taskresults.all()  # type: ignore

        for task in tasks:
            for result in results:
                if result.task.id == task.pk:
                    task.task_result = result
                    break

        return tasks

    def add_check_results(self, checks: "List[Check]") -> "List[Check]":
        results = self.checkresults.all()  # type: ignore

        for check in checks:
            for result in results:
                if result.assigned_check.id == check.pk:
                    check.check_result = result
                    break

        return checks

    def get_agent_policies(self) -> "Dict[str, Optional[Policy]]":
        from checks.models import Check

        site_policy = getattr(self.site, f"{self.monitoring_type}_policy", None)
        client_policy = getattr(self.client, f"{self.monitoring_type}_policy", None)
        default_policy = getattr(
            get_core_settings(), f"{self.monitoring_type}_policy", None
        )

        # prefetch excluded objects on polices only if policy is not Non
        models.prefetch_related_objects(
            [
                policy
                for policy in (self.policy, site_policy, client_policy, default_policy)
                if policy
            ],
            "excluded_agents",
            "excluded_sites",
            "excluded_clients",
            models.Prefetch(
                "policychecks", queryset=Check.objects.select_related("script")
            ),
            "autotasks",
        )

        return {
            "agent_policy": (
                self.policy
                if self.policy and not self.policy.is_agent_excluded(self)
                else None
            ),
            "site_policy": (
                site_policy
                if (site_policy and not site_policy.is_agent_excluded(self))
                and not self.block_policy_inheritance
                else None
            ),
            "client_policy": (
                client_policy
                if (client_policy and not client_policy.is_agent_excluded(self))
                and not self.block_policy_inheritance
                and not self.site.block_policy_inheritance
                else None
            ),
            "default_policy": (
                default_policy
                if (default_policy and not default_policy.is_agent_excluded(self))
                and not self.block_policy_inheritance
                and not self.site.block_policy_inheritance
                and not self.client.block_policy_inheritance
                else None
            ),
        }

    def check_run_interval(self) -> int:
        interval = self.check_interval
        # determine if any agent checks have a custom interval and set the lowest interval
        for check in self.get_checks_with_policies():
            if check.run_interval and check.run_interval < interval:
                # don't allow check runs less than 15s
                interval = 15 if check.run_interval < 15 else check.run_interval

        return interval

    def run_script(
        self,
        scriptpk: int,
        args: List[str] = [],
        timeout: int = 120,
        full: bool = False,
        wait: bool = False,
        run_on_any: bool = False,
        history_pk: int = 0,
        run_as_user: bool = False,
        env_vars: list[str] = [],
    ) -> Any:
        from scripts.models import Script

        script = Script.objects.get(pk=scriptpk)

        # always override if set on script model
        if script.run_as_user:
            run_as_user = True

        parsed_args = script.parse_script_args(self, script.shell, args)
        parsed_env_vars = script.parse_script_env_vars(self, script.shell, env_vars)

        data = {
            "func": "runscriptfull" if full else "runscript",
            "timeout": timeout,
            "script_args": parsed_args,
            "payload": {
                "code": script.code,
                "shell": script.shell,
            },
            "run_as_user": run_as_user,
            "env_vars": parsed_env_vars,
            "nushell_enable_config": settings.NUSHELL_ENABLE_CONFIG,
            "deno_default_permissions": settings.DENO_DEFAULT_PERMISSIONS,
        }

        if history_pk != 0:
            data["id"] = history_pk

        running_agent = self
        if run_on_any:
            nats_ping = {"func": "ping"}

            # try on self first
            r = asyncio.run(self.nats_cmd(nats_ping, timeout=1))

            if r == "pong":
                running_agent = self
            else:
                for agent in Agent.online_agents():
                    r = asyncio.run(agent.nats_cmd(nats_ping, timeout=1))
                    if r == "pong":
                        running_agent = agent
                        break

                if running_agent.pk == self.pk:
                    return "Unable to find an online agent"

        if wait:
            return asyncio.run(running_agent.nats_cmd(data, timeout=timeout, wait=True))
        else:
            asyncio.run(running_agent.nats_cmd(data, wait=False))

        return "ok"

    # auto approves updates
    def approve_updates(self) -> None:
        patch_policy = self.get_patch_policy()

        severity_list = []
        if patch_policy.critical == "approve":
            severity_list.append("Critical")

        if patch_policy.important == "approve":
            severity_list.append("Important")

        if patch_policy.moderate == "approve":
            severity_list.append("Moderate")

        if patch_policy.low == "approve":
            severity_list.append("Low")

        if patch_policy.other == "approve":
            severity_list.append("")

        self.winupdates.filter(severity__in=severity_list, installed=False).exclude(
            action="approve"
        ).update(action="approve")

    # returns agent policy merged with a client or site specific policy
    def get_patch_policy(self) -> "WinUpdatePolicy":
        from winupdate.models import WinUpdatePolicy

        # check if site has a patch policy and if so use it
        patch_policy = None

        agent_policy = self.winupdatepolicy.first()

        if not agent_policy:
            agent_policy = WinUpdatePolicy.objects.create(agent=self)

        # Get the list of policies applied to the agent and select the
        # highest priority one.
        policies = self.get_agent_policies()

        for _, policy in policies.items():
            if policy and policy.active and policy.winupdatepolicy.exists():
                patch_policy = policy.winupdatepolicy.first()
                break

        # if policy still doesn't exist return the agent patch policy
        if not patch_policy:
            return agent_policy

        # patch policy exists. check if any agent settings are set to override patch policy
        if agent_policy.critical != "inherit":
            patch_policy.critical = agent_policy.critical

        if agent_policy.important != "inherit":
            patch_policy.important = agent_policy.important

        if agent_policy.moderate != "inherit":
            patch_policy.moderate = agent_policy.moderate

        if agent_policy.low != "inherit":
            patch_policy.low = agent_policy.low

        if agent_policy.other != "inherit":
            patch_policy.other = agent_policy.other

        if agent_policy.run_time_frequency != "inherit":
            patch_policy.run_time_frequency = agent_policy.run_time_frequency
            patch_policy.run_time_hour = agent_policy.run_time_hour
            patch_policy.run_time_days = agent_policy.run_time_days

        if agent_policy.reboot_after_install != "inherit":
            patch_policy.reboot_after_install = agent_policy.reboot_after_install

        if not agent_policy.reprocess_failed_inherit:
            patch_policy.reprocess_failed = agent_policy.reprocess_failed
            patch_policy.reprocess_failed_times = agent_policy.reprocess_failed_times
            patch_policy.email_if_fail = agent_policy.email_if_fail

        return patch_policy

    def get_approved_update_guids(self) -> list[str]:
        return list(
            self.winupdates.filter(action="approve", installed=False).values_list(  # type: ignore
                "guid", flat=True
            )
        )

    # sets alert template assigned in the following order: policy, site, client, global
    # sets None if nothing is found
    def set_alert_template(self) -> "Optional[AlertTemplate]":
        core = get_core_settings()

        policies = self.get_agent_policies()

        # loop through all policies applied to agent and return an alert_template if found
        processed_policies: List[int] = []
        for key, policy in policies.items():
            # default alert_template will override a default policy with alert template applied
            if (
                "default" in key
                and core.alert_template
                and core.alert_template.is_active
                and not core.alert_template.is_agent_excluded(self)
            ):
                self.alert_template = core.alert_template
                self.save(update_fields=["alert_template"])
                return core.alert_template
            elif (
                policy
                and policy.active
                and policy.pk not in processed_policies
                and policy.alert_template
                and policy.alert_template.is_active
                and not policy.alert_template.is_agent_excluded(self)
            ):
                self.alert_template = policy.alert_template
                self.save(update_fields=["alert_template"])
                return policy.alert_template
            elif (
                "site" in key
                and self.site.alert_template
                and self.site.alert_template.is_active
                and not self.site.alert_template.is_agent_excluded(self)
            ):
                self.alert_template = self.site.alert_template
                self.save(update_fields=["alert_template"])
                return self.site.alert_template
            elif (
                "client" in key
                and self.site.client.alert_template
                and self.site.client.alert_template.is_active
                and not self.site.client.alert_template.is_agent_excluded(self)
            ):
                self.alert_template = self.site.client.alert_template
                self.save(update_fields=["alert_template"])
                return self.site.client.alert_template

        # no alert templates found or agent has been excluded
        self.alert_template = None
        self.save(update_fields=["alert_template"])

        return None

    def get_or_create_alert_if_needed(
        self, alert_template: "Optional[AlertTemplate]"
    ) -> "Optional[Alert]":
        from alerts.models import Alert

        return Alert.create_or_return_availability_alert(
            self, skip_create=not self.should_create_alert(alert_template)
        )

    def get_checks_from_policies(self) -> "List[Check]":
        from automation.models import Policy

        # check if agent is blocking inheritance
        if self.block_policy_inheritance or self.agentchecks.exists():
            cache_key = f"agent_{self.agent_id}_checks"

        elif self.policy:
            cache_key = f"site_{self.monitoring_type}_{self.plat}_{self.site_id}_policy_{self.policy_id}_checks"

        else:
            cache_key = f"site_{self.monitoring_type}_{self.plat}_{self.site_id}_checks"

        cached_checks = cache.get(cache_key)
        if isinstance(cached_checks, list):
            return cached_checks
        else:
            # clear agent checks that have overridden_by_policy set
            self.agentchecks.update(overridden_by_policy=False)  # type: ignore

            # get agent checks based on policies
            checks = Policy.get_policy_checks(self)
            cache.set(cache_key, checks, 600)
            return checks

    def get_tasks_from_policies(self) -> "List[AutomatedTask]":
        from automation.models import Policy

        # check if agent is blocking inheritance
        if self.block_policy_inheritance:
            cache_key = f"agent_{self.agent_id}_tasks"

        elif self.policy:
            cache_key = f"site_{self.monitoring_type}_{self.plat}_{self.site_id}_policy_{self.policy_id}_tasks"

        else:
            cache_key = f"site_{self.monitoring_type}_{self.plat}_{self.site_id}_tasks"

        cached_tasks = cache.get(cache_key)
        if isinstance(cached_tasks, list):
            return cached_tasks
        else:
            # get agent tasks based on policies
            tasks = Policy.get_policy_tasks(self)
            cache.set(cache_key, tasks, 600)
            return tasks

    async def nats_cmd(
        self, data: Dict[Any, Any], timeout: int = 30, wait: bool = True
    ) -> Any:
        opts = setup_nats_options()
        try:
            nc = await nats.connect(**opts)
        except:
            return "natsdown"

        if wait:
            try:
                msg = await nc.request(
                    self.agent_id, msgpack.dumps(data), timeout=timeout
                )
            except TimeoutError:
                ret = "timeout"
            else:
                try:
                    ret = msgpack.loads(msg.data)
                except Exception as e:
                    ret = str(e)
                    logger.error(e)

            await nc.close()
            return ret
        else:
            await nc.publish(self.agent_id, msgpack.dumps(data))
            await nc.flush()
            await nc.close()

    def recover(self, mode: str, mesh_uri: str, wait: bool = True) -> tuple[str, bool]:
        """
        Return type: tuple(message: str, error: bool)
        """
        if mode == "tacagent":
            if self.plat == AgentPlat.LINUX:
                cmd = "systemctl restart tacticalagent.service"
                shell = 3
            elif self.plat == AgentPlat.DARWIN:
                cmd = "launchctl kickstart -k system/tacticalagent"
                shell = 3
            else:
                cmd = "net stop tacticalrmm & taskkill /F /IM tacticalrmm.exe & net start tacticalrmm"
                shell = 1

            asyncio.run(
                send_command_with_mesh(cmd, mesh_uri, self.mesh_node_id, shell, 0)
            )
            return "ok", False

        elif mode == "mesh":
            data = {"func": "recover", "payload": {"mode": mode}}
            if wait:
                r = asyncio.run(self.nats_cmd(data, timeout=20))
                if r == "ok":
                    return "ok", False
                else:
                    return str(r), True
            else:
                asyncio.run(self.nats_cmd(data, timeout=20, wait=False))

            return "ok", False

        return "invalid", True

    @staticmethod
    def serialize(agent: "Agent") -> Dict[str, Any]:
        # serializes the agent and returns json
        from .serializers import AgentAuditSerializer

        return AgentAuditSerializer(agent).data

    def delete_superseded_updates(self) -> None:
        with suppress(Exception):
            pks = []  # list of pks to delete
            kbs = list(self.winupdates.values_list("kb", flat=True))
            d = Counter(kbs)
            dupes = [k for k, v in d.items() if v > 1]

            for dupe in dupes:
                titles = self.winupdates.filter(kb=dupe).values_list("title", flat=True)
                # extract the version from the title and sort from oldest to newest
                # skip if no version info is available therefore nothing to parse
                try:
                    matches = r"(Version|Versão)"
                    pattern = r"\(" + matches + r"(.*?)\)"
                    vers = [
                        re.search(pattern, i, flags=re.IGNORECASE).group(2).strip()
                        for i in titles
                    ]
                    sorted_vers = sorted(vers, key=LooseVersion)
                except:
                    continue
                # append all but the latest version to our list of pks to delete
                for ver in sorted_vers[:-1]:
                    q = self.winupdates.filter(kb=dupe).filter(title__contains=ver)
                    pks.append(q.first().pk)

            pks = list(set(pks))
            self.winupdates.filter(pk__in=pks).delete()

    def should_create_alert(
        self, alert_template: "Optional[AlertTemplate]" = None
    ) -> bool:
        has_agent_notification = (
            self.overdue_dashboard_alert
            or self.overdue_email_alert
            or self.overdue_text_alert
        )
        has_alert_template_notification = alert_template and (
            alert_template.agent_always_alert
            or alert_template.agent_always_email
            or alert_template.agent_always_text
        )

        return bool(
            has_agent_notification
            or has_alert_template_notification
            or has_webhook(alert_template, "agent")
            or has_script_actions(alert_template, "agent")
        )

    def send_outage_email(self) -> None:
        CORE = get_core_settings()

        CORE.send_mail(
            f"{self.client.name}, {self.site.name}, {self.hostname} - data overdue",
            (
                f"Data has not been received from client {self.client.name}, "
                f"site {self.site.name}, "
                f"agent {self.hostname} "
                "within the expected time."
            ),
            alert_template=self.alert_template,
        )

    def send_recovery_email(self) -> None:
        CORE = get_core_settings()

        CORE.send_mail(
            f"{self.client.name}, {self.site.name}, {self.hostname} - data received",
            (
                f"Data has been received from client {self.client.name}, "
                f"site {self.site.name}, "
                f"agent {self.hostname} "
                "after an interruption in data transmission."
            ),
            alert_template=self.alert_template,
        )

    def send_outage_sms(self) -> None:
        CORE = get_core_settings()

        CORE.send_sms(
            f"{self.client.name}, {self.site.name}, {self.hostname} - data overdue",
            alert_template=self.alert_template,
        )

    def send_recovery_sms(self) -> None:
        CORE = get_core_settings()

        CORE.send_sms(
            f"{self.client.name}, {self.site.name}, {self.hostname} - data received",
            alert_template=self.alert_template,
        )


class Note(models.Model):
    objects = PermissionQuerySet.as_manager()

    agent = models.ForeignKey(
        Agent,
        related_name="notes",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        "accounts.User",
        related_name="user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    note = models.TextField(null=True, blank=True)
    entry_time = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.agent.hostname


class AgentCustomField(models.Model):
    objects = PermissionQuerySet.as_manager()

    agent = models.ForeignKey(
        Agent,
        related_name="custom_fields",
        on_delete=models.CASCADE,
    )

    field = models.ForeignKey(
        "core.CustomField",
        related_name="agent_fields",
        on_delete=models.CASCADE,
    )

    string_value = models.TextField(null=True, blank=True)
    bool_value = models.BooleanField(blank=True, default=False)
    multiple_value = ArrayField(
        models.TextField(null=True, blank=True),
        null=True,
        blank=True,
        default=list,
    )

    class Meta:
        unique_together = (("agent", "field"),)

    def __str__(self) -> str:
        return self.field.name

    @property
    def value(self) -> Union[List[Any], bool, str]:
        if self.field.type == CustomFieldType.MULTIPLE:
            return cast(List[str], self.multiple_value)
        elif self.field.type == CustomFieldType.CHECKBOX:
            return self.bool_value

        return cast(str, self.string_value)

    def save_to_field(self, value: Union[List[Any], bool, str]) -> None:
        if self.field.type in (
            CustomFieldType.TEXT,
            CustomFieldType.NUMBER,
            CustomFieldType.SINGLE,
            CustomFieldType.DATETIME,
        ):
            self.string_value = cast(str, value)
            self.save()
        elif self.field.type == CustomFieldType.MULTIPLE:
            self.multiple_value = value.split(",")
            self.save()
        elif self.field.type == CustomFieldType.CHECKBOX:
            self.bool_value = bool(value)
            self.save()


class AgentHistory(models.Model):
    objects = PermissionQuerySet.as_manager()

    id = models.BigAutoField(primary_key=True)
    agent = models.ForeignKey(
        Agent,
        related_name="history",
        on_delete=models.CASCADE,
    )
    time = models.DateTimeField(auto_now_add=True)
    type: "AgentHistoryType" = models.CharField(
        max_length=50,
        choices=AgentHistoryType.choices,
        default=AgentHistoryType.CMD_RUN,
    )
    command = models.TextField(null=True, blank=True, default="")
    username = models.CharField(max_length=255, default="system")
    results = models.TextField(null=True, blank=True)
    script = models.ForeignKey(
        "scripts.Script",
        null=True,
        blank=True,
        related_name="history",
        on_delete=models.SET_NULL,
    )
    script_results = models.JSONField(null=True, blank=True)
    custom_field = models.ForeignKey(
        "core.CustomField",
        null=True,
        blank=True,
        related_name="history",
        on_delete=models.SET_NULL,
    )
    collector_all_output = models.BooleanField(default=False)
    save_to_agent_note = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.agent.hostname} - {self.type}"
