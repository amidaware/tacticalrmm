import requests
import datetime as dt
import time
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA3_384
from Crypto.Util.Padding import pad
import validators
import random
import re
import string
from collections import Counter
from loguru import logger
from packaging import version as pyver
from distutils.version import LooseVersion

from django.db import models
from django.conf import settings
from django.utils import timezone as djangotime

from core.models import CoreSettings, TZ_CHOICES
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
    def winsalt_dl(self):
        if self.arch == "64":
            return settings.SALT_64
        elif self.arch == "32":
            return settings.SALT_32
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
        offline = djangotime.now() - djangotime.timedelta(minutes=6)
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
    def has_patches_pending(self):

        if self.winupdates.filter(action="approve").filter(installed=False).exists():
            return True
        else:
            return False

    @property
    def checks(self):
        total, passing, failing = 0, 0, 0

        if self.agentchecks.exists():
            for i in self.agentchecks.all():
                total += 1
                if i.status == "passing":
                    passing += 1
                elif i.status == "failing":
                    failing += 1

        has_failing_checks = True if failing > 0 else False

        ret = {
            "total": total,
            "passing": passing,
            "failing": failing,
            "has_failing_checks": has_failing_checks,
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

            return f"{make} {model}"
        except:
            pass

        try:
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

    # auto approves updates
    def approve_updates(self):
        patch_policy = self.get_patch_policy()

        updates = list()
        if patch_policy.critical == "approve":
            updates += self.winupdates.filter(
                severity="Critical", installed=False
            ).exclude(action="approve")

        if patch_policy.important == "approve":
            updates += self.winupdates.filter(
                severity="Important", installed=False
            ).exclude(action="approve")

        if patch_policy.moderate == "approve":
            updates += self.winupdates.filter(
                severity="Moderate", installed=False
            ).exclude(action="approve")

        if patch_policy.low == "approve":
            updates += self.winupdates.filter(severity="Low", installed=False).exclude(
                action="approve"
            )

        if patch_policy.other == "approve":
            updates += self.winupdates.filter(severity="", installed=False).exclude(
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
        agent_policy = self.winupdatepolicy.get()

        if self.monitoring_type == "server":
            # check agent policy first which should override client or site policy
            if self.policy and self.policy.winupdatepolicy.exists():
                patch_policy = self.policy.winupdatepolicy.get()

            # check site policy if agent policy doesn't have one
            elif site.server_policy and site.server_policy.winupdatepolicy.exists():
                patch_policy = site.server_policy.winupdatepolicy.get()

            # if site doesn't have a patch policy check the client
            elif (
                site.client.server_policy
                and site.client.server_policy.winupdatepolicy.exists()
            ):
                patch_policy = site.client.server_policy.winupdatepolicy.get()

            # if patch policy still doesn't exist check default policy
            elif (
                core_settings.server_policy
                and core_settings.server_policy.winupdatepolicy.exists()
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
                patch_policy = site.workstation_policy.winupdatepolicy.get()

            # if site doesn't have a patch policy check the client
            elif (
                site.client.workstation_policy
                and site.client.workstation_policy.winupdatepolicy.exists()
            ):
                patch_policy = site.client.workstation_policy.winupdatepolicy.get()

            # if patch policy still doesn't exist check default policy
            elif (
                core_settings.workstation_policy
                and core_settings.workstation_policy.winupdatepolicy.exists()
            ):
                patch_policy = core_settings.workstation_policy.winupdatepolicy.get()

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

    # clear is used to delete managed policy checks from agent
    # parent_checks specifies a list of checks to delete from agent with matching parent_check field
    def generate_checks_from_policies(self, clear=False):
        from automation.models import Policy

        # Clear agent checks managed by policy
        if clear:
            self.agentchecks.filter(managed_by_policy=True).delete()

        # Clear agent checks that have overriden_by_policy set
        self.agentchecks.update(overriden_by_policy=False)

        # Generate checks based on policies
        Policy.generate_policy_checks(self)

    # clear is used to delete managed policy tasks from agent
    # parent_tasks specifies a list of tasks to delete from agent with matching parent_task field
    def generate_tasks_from_policies(self, clear=False):
        from autotasks.tasks import delete_win_task_schedule
        from automation.models import Policy

        # Clear agent tasks managed by policy
        if clear:
            for task in self.autotasks.filter(managed_by_policy=True):
                delete_win_task_schedule.delay(task.pk)

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

    def salt_api_cmd(self, **kwargs):

        # salt should always timeout first before the requests' timeout
        try:
            timeout = kwargs["timeout"]
        except KeyError:
            # default timeout
            timeout = 15
            salt_timeout = 12
        else:
            if timeout < 8:
                timeout = 8
                salt_timeout = 5
            else:
                salt_timeout = timeout - 3

        json = {
            "client": "local",
            "tgt": self.salt_id,
            "fun": kwargs["func"],
            "timeout": salt_timeout,
            "username": settings.SALT_USERNAME,
            "password": settings.SALT_PASSWORD,
            "eauth": "pam",
        }

        if "arg" in kwargs:
            json.update({"arg": kwargs["arg"]})
        if "kwargs" in kwargs:
            json.update({"kwarg": kwargs["kwargs"]})

        try:
            resp = requests.post(
                f"http://{settings.SALT_HOST}:8123/run",
                json=[json],
                timeout=timeout,
            )
        except Exception:
            return "timeout"

        try:
            ret = resp.json()["return"][0][self.salt_id]
        except Exception as e:
            logger.error(f"{self.salt_id}: {e}")
            return "error"
        else:
            return ret

    def salt_api_async(self, **kwargs):

        json = {
            "client": "local_async",
            "tgt": self.salt_id,
            "fun": kwargs["func"],
            "username": settings.SALT_USERNAME,
            "password": settings.SALT_PASSWORD,
            "eauth": "pam",
        }

        if "arg" in kwargs:
            json.update({"arg": kwargs["arg"]})
        if "kwargs" in kwargs:
            json.update({"kwarg": kwargs["kwargs"]})

        try:
            resp = requests.post(f"http://{settings.SALT_HOST}:8123/run", json=[json])
        except Exception:
            return "timeout"

        return resp

    @staticmethod
    def serialize(agent):
        # serializes the agent and returns json
        from .serializers import AgentEditSerializer

        ret = AgentEditSerializer(agent).data
        del ret["all_timezones"]
        return ret

    @staticmethod
    def salt_batch_async(**kwargs):
        assert isinstance(kwargs["minions"], list)

        json = {
            "client": "local_async",
            "tgt_type": "list",
            "tgt": kwargs["minions"],
            "fun": kwargs["func"],
            "username": settings.SALT_USERNAME,
            "password": settings.SALT_PASSWORD,
            "eauth": "pam",
        }

        if "arg" in kwargs:
            json.update({"arg": kwargs["arg"]})
        if "kwargs" in kwargs:
            json.update({"kwarg": kwargs["kwargs"]})

        try:
            resp = requests.post(f"http://{settings.SALT_HOST}:8123/run", json=[json])
        except Exception:
            return "timeout"

        return resp

    def schedule_reboot(self, obj):

        start_date = dt.datetime.strftime(obj, "%Y-%m-%d")
        start_time = dt.datetime.strftime(obj, "%H:%M")

        # let windows task scheduler automatically delete the task after it runs
        end_obj = obj + dt.timedelta(minutes=15)
        end_date = dt.datetime.strftime(end_obj, "%Y-%m-%d")
        end_time = dt.datetime.strftime(end_obj, "%H:%M")

        task_name = "TacticalRMM_SchedReboot_" + "".join(
            random.choice(string.ascii_letters) for _ in range(10)
        )

        r = self.salt_api_cmd(
            timeout=15,
            func="task.create_task",
            arg=[
                f"name={task_name}",
                "force=True",
                "action_type=Execute",
                'cmd="C:\\Windows\\System32\\shutdown.exe"',
                'arguments="/r /t 5 /f"',
                "trigger_type=Once",
                f'start_date="{start_date}"',
                f'start_time="{start_time}"',
                f'end_date="{end_date}"',
                f'end_time="{end_time}"',
                "ac_only=False",
                "stop_if_on_batteries=False",
                "delete_after=Immediately",
            ],
        )

        if r == "error" or (isinstance(r, bool) and not r):
            return "failed"
        elif r == "timeout":
            return "timeout"
        elif isinstance(r, bool) and r:
            from logs.models import PendingAction

            details = {
                "taskname": task_name,
                "time": str(obj),
            }
            PendingAction(agent=self, action_type="schedreboot", details=details).save()

            nice_time = dt.datetime.strftime(obj, "%B %d, %Y at %I:%M %p")
            return {"msg": {"time": nice_time, "agent": self.hostname}}
        else:
            return "failed"

    def not_supported(self, version_added):
        if pyver.parse(self.version) < pyver.parse(version_added):
            return True

        return False

    def delete_superseded_updates(self):
        try:
            pks = []  # list of pks to delete
            kbs = list(self.winupdates.values_list("kb", flat=True))
            d = Counter(kbs)
            dupes = [k for k, v in d.items() if v > 1]

            for dupe in dupes:
                titles = self.winupdates.filter(kb=dupe).values_list("title", flat=True)
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
                    q = self.winupdates.filter(kb=dupe).filter(title__contains=ver)
                    pks.append(q.first().pk)

            pks = list(set(pks))
            self.winupdates.filter(pk__in=pks).delete()
        except:
            pass

    # define how the agent should handle pending actions
    def handle_pending_actions(self):
        pending_actions = self.pendingactions.filter(status="pending")

        for action in pending_actions:
            if action.action_type == "taskaction":
                from autotasks.tasks import (
                    create_win_task_schedule,
                    enable_or_disable_win_task,
                    delete_win_task_schedule,
                )

                task_id = action.details["task_id"]

                if action.details["action"] == "taskcreate":
                    create_win_task_schedule.delay(task_id, pending_action=action.id)
                elif action.details["action"] == "tasktoggle":
                    enable_or_disable_win_task.delay(
                        task_id, action.details["value"], pending_action=action.id
                    )
                elif action.details["action"] == "taskdelete":
                    delete_win_task_schedule.delay(task_id, pending_action=action.id)


class AgentOutage(models.Model):
    agent = models.ForeignKey(
        Agent,
        related_name="agentoutages",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    outage_time = models.DateTimeField(auto_now_add=True)
    recovery_time = models.DateTimeField(null=True, blank=True)
    outage_email_sent = models.BooleanField(default=False)
    outage_sms_sent = models.BooleanField(default=False)
    recovery_email_sent = models.BooleanField(default=False)
    recovery_sms_sent = models.BooleanField(default=False)

    @property
    def is_active(self):
        return False if self.recovery_time else True

    def send_outage_email(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        CORE.send_mail(
            f"{self.agent.client.name}, {self.agent.site.name}, {self.agent.hostname} - data overdue",
            (
                f"Data has not been received from client {self.agent.client.name}, "
                f"site {self.agent.site.name}, "
                f"agent {self.agent.hostname} "
                "within the expected time."
            ),
        )

    def send_recovery_email(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        CORE.send_mail(
            f"{self.agent.client.name}, {self.agent.site.name}, {self.agent.hostname} - data received",
            (
                f"Data has been received from client {self.agent.client.name}, "
                f"site {self.agent.site.name}, "
                f"agent {self.agent.hostname} "
                "after an interruption in data transmission."
            ),
        )

    def send_outage_sms(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        CORE.send_sms(
            f"{self.agent.client.name}, {self.agent.site.name}, {self.agent.hostname} - data overdue"
        )

    def send_recovery_sms(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        CORE.send_sms(
            f"{self.agent.client.name}, {self.agent.site.name}, {self.agent.hostname} - data received"
        )

    def __str__(self):
        return self.agent.hostname


RECOVERY_CHOICES = [
    ("salt", "Salt"),
    ("mesh", "Mesh"),
    ("command", "Command"),
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

    def send(self):
        ret = {"recovery": self.mode}
        if self.mode == "command":
            ret["cmd"] = self.command
        return ret


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
