import asyncio
import base64
import re
import time
from collections import Counter
from distutils.version import LooseVersion
from typing import Any

import msgpack
import validators
from Crypto.Cipher import AES
from Crypto.Hash import SHA3_384
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone as djangotime
from loguru import logger
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrTimeout

from core.models import TZ_CHOICES, CoreSettings
from logs.models import BaseAuditModel

logger.configure(**settings.LOG_CONFIG)


class Agent(BaseAuditModel):
    version = models.CharField(default="0.1.0", max_length=255)
    salt_ver = models.CharField(default="1.0.3", max_length=255)
    operating_system = models.CharField(null=True, blank=True, max_length=255)
    plat = models.CharField(max_length=255, null=True, blank=True)
    plat_release = models.CharField(max_length=255, null=True, blank=True)
    hostname = models.CharField(max_length=255)
    salt_id = models.CharField(null=True, blank=True, max_length=255)
    local_ip = models.TextField(null=True, blank=True)  # deprecated
    agent_id = models.CharField(max_length=200)
    last_seen = models.DateTimeField(null=True, blank=True)
    services = models.JSONField(null=True, blank=True)
    public_ip = models.CharField(null=True, max_length=255)
    total_ram = models.IntegerField(null=True, blank=True)
    used_ram = models.IntegerField(null=True, blank=True)  # deprecated
    disks = models.JSONField(null=True, blank=True)
    boot_time = models.FloatField(null=True, blank=True)
    logged_in_username = models.CharField(null=True, blank=True, max_length=255)
    last_logged_in_user = models.CharField(null=True, blank=True, max_length=255)
    antivirus = models.CharField(default="n/a", max_length=255)  # deprecated
    monitoring_type = models.CharField(max_length=30)
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
    pending_actions_count = models.PositiveIntegerField(default=0)
    has_patches_pending = models.BooleanField(default=False)
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
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    policy = models.ForeignKey(
        "automation.Policy",
        related_name="agents",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def save(self, *args, **kwargs):

        # get old agent if exists
        old_agent = type(self).objects.get(pk=self.pk) if self.pk else None
        super(BaseAuditModel, self).save(*args, **kwargs)

        # check if new agent has been created
        # or check if policy have changed on agent
        # or if site has changed on agent and if so generate-policies
        # or if agent was changed from server or workstation
        if (
            not old_agent
            or (old_agent and old_agent.policy != self.policy)
            or (old_agent.site != self.site)
            or (old_agent.monitoring_type != self.monitoring_type)
            or (old_agent.block_policy_inheritance != self.block_policy_inheritance)
        ):
            self.generate_checks_from_policies()
            self.generate_tasks_from_policies()

    def __str__(self):
        return self.hostname

    @property
    def client(self):
        return self.site.client

    @property
    def timezone(self):
        # return the default timezone unless the timezone is explicity set per agent
        if self.time_zone is not None:
            return self.time_zone
        else:
            from core.models import CoreSettings

            return CoreSettings.objects.first().default_time_zone

    @property
    def arch(self):
        if self.operating_system is not None:
            if "64 bit" in self.operating_system or "64bit" in self.operating_system:
                return "64"
            elif "32 bit" in self.operating_system or "32bit" in self.operating_system:
                return "32"
        return None

    @property
    def winagent_dl(self):
        if self.arch == "64":
            return settings.DL_64
        elif self.arch == "32":
            return settings.DL_32
        return None

    @property
    def win_inno_exe(self):
        if self.arch == "64":
            return f"winagent-v{settings.LATEST_AGENT_VER}.exe"
        elif self.arch == "32":
            return f"winagent-v{settings.LATEST_AGENT_VER}-x86.exe"
        return None

    @property
    def status(self):
        offline = djangotime.now() - djangotime.timedelta(minutes=self.offline_time)
        overdue = djangotime.now() - djangotime.timedelta(minutes=self.overdue_time)

        if self.last_seen is not None:
            if (self.last_seen < offline) and (self.last_seen > overdue):
                return "offline"
            elif (self.last_seen < offline) and (self.last_seen < overdue):
                return "overdue"
            else:
                return "online"
        else:
            return "offline"

    @property
    def checks(self):
        total, passing, failing, warning, info = 0, 0, 0, 0, 0

        if self.agentchecks.exists():  # type: ignore
            for i in self.agentchecks.all():  # type: ignore
                total += 1
                if i.status == "passing":
                    passing += 1
                elif i.status == "failing":
                    if i.alert_severity == "error":
                        failing += 1
                    elif i.alert_severity == "warning":
                        warning += 1
                    elif i.alert_severity == "info":
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
    def cpu_model(self):
        ret = []
        try:
            cpus = self.wmi_detail["cpu"]
            for cpu in cpus:
                ret.append([x["Name"] for x in cpu if "Name" in x][0])
            return ret
        except:
            return ["unknown cpu model"]

    @property
    def graphics(self):
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
    def local_ips(self):
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
            return ret[0]
        else:
            return ", ".join(ret) if ret else "error getting local ips"

    @property
    def make_model(self):
        try:
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
        except:
            pass

        try:
            comp_sys_prod = self.wmi_detail["comp_sys_prod"][0]
            return [x["Version"] for x in comp_sys_prod if "Version" in x][0]
        except:
            pass

        return "unknown make/model"

    @property
    def physical_disks(self):
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

    def check_run_interval(self) -> int:
        interval = self.check_interval
        # determine if any agent checks have a custom interval and set the lowest interval
        for check in self.agentchecks.filter(overriden_by_policy=False):  # type: ignore
            if check.run_interval and check.run_interval < interval:

                # don't allow check runs less than 15s
                if check.run_interval < 15:
                    interval = 15
                else:
                    interval = check.run_interval

        return interval

    def run_script(
        self,
        scriptpk: int,
        args: list[str] = [],
        timeout: int = 120,
        full: bool = False,
        wait: bool = False,
        run_on_any: bool = False,
    ) -> Any:

        from scripts.models import Script

        script = Script.objects.get(pk=scriptpk)

        parsed_args = script.parse_script_args(self, script.shell, args)

        data = {
            "func": "runscriptfull" if full else "runscript",
            "timeout": timeout,
            "script_args": parsed_args,
            "payload": {
                "code": script.code,
                "shell": script.shell,
            },
        }

        running_agent = self
        if run_on_any:
            nats_ping = {"func": "ping"}

            # try on self first
            r = asyncio.run(self.nats_cmd(nats_ping, timeout=1))

            if r == "pong":
                running_agent = self
            else:
                online = [
                    agent
                    for agent in Agent.objects.only(
                        "pk", "agent_id", "last_seen", "overdue_time", "offline_time"
                    )
                    if agent.status == "online"
                ]

                for agent in online:
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
    def approve_updates(self):
        patch_policy = self.get_patch_policy()

        updates = list()
        if patch_policy.critical == "approve":
            updates += self.winupdates.filter(  # type: ignore
                severity="Critical", installed=False
            ).exclude(action="approve")

        if patch_policy.important == "approve":
            updates += self.winupdates.filter(  # type: ignore
                severity="Important", installed=False
            ).exclude(action="approve")

        if patch_policy.moderate == "approve":
            updates += self.winupdates.filter(  # type: ignore
                severity="Moderate", installed=False
            ).exclude(action="approve")

        if patch_policy.low == "approve":
            updates += self.winupdates.filter(severity="Low", installed=False).exclude(  # type: ignore
                action="approve"
            )

        if patch_policy.other == "approve":
            updates += self.winupdates.filter(severity="", installed=False).exclude(  # type: ignore
                action="approve"
            )

        for update in updates:
            update.action = "approve"
            update.save(update_fields=["action"])

    # returns agent policy merged with a client or site specific policy
    def get_patch_policy(self):

        # check if site has a patch policy and if so use it
        site = self.site
        core_settings = CoreSettings.objects.first()
        patch_policy = None
        agent_policy = self.winupdatepolicy.get()  # type: ignore

        if self.monitoring_type == "server":
            # check agent policy first which should override client or site policy
            if self.policy and self.policy.winupdatepolicy.exists():
                patch_policy = self.policy.winupdatepolicy.get()

            # check site policy if agent policy doesn't have one
            elif site.server_policy and site.server_policy.winupdatepolicy.exists():
                # make sure agent isn;t blocking policy inheritance
                if not self.block_policy_inheritance:
                    patch_policy = site.server_policy.winupdatepolicy.get()

            # if site doesn't have a patch policy check the client
            elif (
                site.client.server_policy
                and site.client.server_policy.winupdatepolicy.exists()
            ):
                # make sure agent and site are not blocking inheritance
                if (
                    not self.block_policy_inheritance
                    and not site.block_policy_inheritance
                ):
                    patch_policy = site.client.server_policy.winupdatepolicy.get()

            # if patch policy still doesn't exist check default policy
            elif (
                core_settings.server_policy
                and core_settings.server_policy.winupdatepolicy.exists()
            ):
                # make sure agent site and client are not blocking inheritance
                if (
                    not self.block_policy_inheritance
                    and not site.block_policy_inheritance
                    and not site.client.block_policy_inheritance
                ):
                    patch_policy = core_settings.server_policy.winupdatepolicy.get()

        elif self.monitoring_type == "workstation":
            # check agent policy first which should override client or site policy
            if self.policy and self.policy.winupdatepolicy.exists():
                patch_policy = self.policy.winupdatepolicy.get()

            elif (
                site.workstation_policy
                and site.workstation_policy.winupdatepolicy.exists()
            ):
                # make sure agent isn;t blocking policy inheritance
                if not self.block_policy_inheritance:
                    patch_policy = site.workstation_policy.winupdatepolicy.get()

            # if site doesn't have a patch policy check the client
            elif (
                site.client.workstation_policy
                and site.client.workstation_policy.winupdatepolicy.exists()
            ):
                # make sure agent and site are not blocking inheritance
                if (
                    not self.block_policy_inheritance
                    and not site.block_policy_inheritance
                ):
                    patch_policy = site.client.workstation_policy.winupdatepolicy.get()

            # if patch policy still doesn't exist check default policy
            elif (
                core_settings.workstation_policy
                and core_settings.workstation_policy.winupdatepolicy.exists()
            ):
                # make sure agent site and client are not blocking inheritance
                if (
                    not self.block_policy_inheritance
                    and not site.block_policy_inheritance
                    and not site.client.block_policy_inheritance
                ):
                    patch_policy = (
                        core_settings.workstation_policy.winupdatepolicy.get()
                    )

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
    def set_alert_template(self):

        site = self.site
        client = self.client
        core = CoreSettings.objects.first()

        templates = list()
        # check if alert template is on a policy assigned to agent
        if (
            self.policy
            and self.policy.alert_template
            and self.policy.alert_template.is_active
        ):
            templates.append(self.policy.alert_template)

        # check if policy with alert template is assigned to the site
        if (
            self.monitoring_type == "server"
            and site.server_policy
            and site.server_policy.alert_template
            and site.server_policy.alert_template.is_active
            and not self.block_policy_inheritance
        ):
            templates.append(site.server_policy.alert_template)
        if (
            self.monitoring_type == "workstation"
            and site.workstation_policy
            and site.workstation_policy.alert_template
            and site.workstation_policy.alert_template.is_active
            and not self.block_policy_inheritance
        ):
            templates.append(site.workstation_policy.alert_template)

        # check if alert template is assigned to site
        if site.alert_template and site.alert_template.is_active:
            templates.append(site.alert_template)

        # check if policy with alert template is assigned to the client
        if (
            self.monitoring_type == "server"
            and client.server_policy
            and client.server_policy.alert_template
            and client.server_policy.alert_template.is_active
            and not self.block_policy_inheritance
            and not site.block_policy_inheritance
        ):
            templates.append(client.server_policy.alert_template)
        if (
            self.monitoring_type == "workstation"
            and client.workstation_policy
            and client.workstation_policy.alert_template
            and client.workstation_policy.alert_template.is_active
            and not self.block_policy_inheritance
            and not site.block_policy_inheritance
        ):
            templates.append(client.workstation_policy.alert_template)

        # check if alert template is on client and return
        if (
            client.alert_template
            and client.alert_template.is_active
            and not self.block_policy_inheritance
            and not site.block_policy_inheritance
        ):
            templates.append(client.alert_template)

        # check if alert template is applied globally and return
        if (
            core.alert_template
            and core.alert_template.is_active
            and not self.block_policy_inheritance
            and not site.block_policy_inheritance
            and not client.block_policy_inheritance
        ):
            templates.append(core.alert_template)

        # if agent is a workstation, check if policy with alert template is assigned to the site, client, or core
        if (
            self.monitoring_type == "server"
            and core.server_policy
            and core.server_policy.alert_template
            and core.server_policy.alert_template.is_active
            and not self.block_policy_inheritance
            and not site.block_policy_inheritance
            and not client.block_policy_inheritance
        ):
            templates.append(core.server_policy.alert_template)
        if (
            self.monitoring_type == "workstation"
            and core.workstation_policy
            and core.workstation_policy.alert_template
            and core.workstation_policy.alert_template.is_active
            and not self.block_policy_inheritance
            and not site.block_policy_inheritance
            and not client.block_policy_inheritance
        ):
            templates.append(core.workstation_policy.alert_template)

        # go through the templates and return the first one that isn't excluded
        for template in templates:
            # check if client, site, or agent has been excluded from template
            if (
                client.pk
                in template.excluded_clients.all().values_list("pk", flat=True)
                or site.pk in template.excluded_sites.all().values_list("pk", flat=True)
                or self.pk
                in template.excluded_agents.all()
                .only("pk")
                .values_list("pk", flat=True)
            ):
                continue

            # check if template is excluding desktops
            elif (
                self.monitoring_type == "workstation" and template.exclude_workstations
            ):
                continue

            # check if template is excluding servers
            elif self.monitoring_type == "server" and template.exclude_servers:
                continue

            else:
                # save alert_template to agent cache field
                self.alert_template = template
                self.save()

                return template

        # no alert templates found or agent has been excluded
        self.alert_template = None
        self.save()

        return None

    def generate_checks_from_policies(self):
        from automation.models import Policy

        # Clear agent checks that have overriden_by_policy set
        self.agentchecks.update(overriden_by_policy=False)  # type: ignore

        # Generate checks based on policies
        Policy.generate_policy_checks(self)

    def generate_tasks_from_policies(self):
        from automation.models import Policy

        # Generate tasks based on policies
        Policy.generate_policy_tasks(self)

    # https://github.com/Ylianst/MeshCentral/issues/59#issuecomment-521965347
    def get_login_token(self, key, user, action=3):
        try:
            key = bytes.fromhex(key)
            key1 = key[0:48]
            key2 = key[48:]
            msg = '{{"a":{}, "u":"{}","time":{}}}'.format(
                action, user, int(time.time())
            )
            iv = get_random_bytes(16)

            # sha
            h = SHA3_384.new()
            h.update(key1)
            hashed_msg = h.digest() + msg.encode()

            # aes
            cipher = AES.new(key2, AES.MODE_CBC, iv)
            msg = cipher.encrypt(pad(hashed_msg, 16))

            return base64.b64encode(iv + msg, altchars=b"@$").decode("utf-8")
        except Exception:
            return "err"

    async def nats_cmd(self, data: dict, timeout: int = 30, wait: bool = True):
        nc = NATS()
        options = {
            "servers": f"tls://{settings.ALLOWED_HOSTS[0]}:4222",
            "user": "tacticalrmm",
            "password": settings.SECRET_KEY,
            "connect_timeout": 3,
            "max_reconnect_attempts": 2,
        }
        try:
            await nc.connect(**options)
        except:
            return "natsdown"

        if wait:
            try:
                msg = await nc.request(
                    self.agent_id, msgpack.dumps(data), timeout=timeout
                )
            except ErrTimeout:
                ret = "timeout"
            else:
                try:
                    ret = msgpack.loads(msg.data)  # type: ignore
                except Exception as e:
                    logger.error(e)
                    ret = str(e)

            await nc.close()
            return ret
        else:
            await nc.publish(self.agent_id, msgpack.dumps(data))
            await nc.flush()
            await nc.close()

    @staticmethod
    def serialize(agent):
        # serializes the agent and returns json
        from .serializers import AgentEditSerializer

        ret = AgentEditSerializer(agent).data
        del ret["all_timezones"]
        del ret["client"]
        return ret

    def delete_superseded_updates(self):
        try:
            pks = []  # list of pks to delete
            kbs = list(self.winupdates.values_list("kb", flat=True))  # type: ignore
            d = Counter(kbs)
            dupes = [k for k, v in d.items() if v > 1]

            for dupe in dupes:
                titles = self.winupdates.filter(kb=dupe).values_list("title", flat=True)  # type: ignore
                # extract the version from the title and sort from oldest to newest
                # skip if no version info is available therefore nothing to parse
                try:
                    vers = [
                        re.search(r"\(Version(.*?)\)", i).group(1).strip()
                        for i in titles
                    ]
                    sorted_vers = sorted(vers, key=LooseVersion)
                except:
                    continue
                # append all but the latest version to our list of pks to delete
                for ver in sorted_vers[:-1]:
                    q = self.winupdates.filter(kb=dupe).filter(title__contains=ver)  # type: ignore
                    pks.append(q.first().pk)

            pks = list(set(pks))
            self.winupdates.filter(pk__in=pks).delete()  # type: ignore
        except:
            pass

    def should_create_alert(self, alert_template=None):
        return (
            self.overdue_dashboard_alert
            or self.overdue_email_alert
            or self.overdue_text_alert
            or (
                alert_template
                and (
                    alert_template.agent_always_alert
                    or alert_template.agent_always_email
                    or alert_template.agent_always_text
                )
            )
        )

    def send_outage_email(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
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

    def send_recovery_email(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
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

    def send_outage_sms(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        CORE.send_sms(
            f"{self.client.name}, {self.site.name}, {self.hostname} - data overdue",
            alert_template=self.alert_template,
        )

    def send_recovery_sms(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        CORE.send_sms(
            f"{self.client.name}, {self.site.name}, {self.hostname} - data received",
            alert_template=self.alert_template,
        )


RECOVERY_CHOICES = [
    ("salt", "Salt"),
    ("mesh", "Mesh"),
    ("command", "Command"),
    ("rpc", "Nats RPC"),
    ("checkrunner", "Checkrunner"),
]


class RecoveryAction(models.Model):
    agent = models.ForeignKey(
        Agent,
        related_name="recoveryactions",
        on_delete=models.CASCADE,
    )
    mode = models.CharField(max_length=50, choices=RECOVERY_CHOICES, default="mesh")
    command = models.TextField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.agent.hostname} - {self.mode}"


class Note(models.Model):
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

    def __str__(self):
        return self.agent.hostname


class AgentCustomField(models.Model):
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

    def __str__(self):
        return self.field

    @property
    def value(self):
        if self.field.type == "multiple":
            return self.multiple_value
        elif self.field.type == "checkbox":
            return self.bool_value
        else:
            return self.string_value
