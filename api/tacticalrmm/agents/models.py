import requests
import datetime as dt
import time
import hashlib
import secrets
import base64
from Crypto.Cipher import AES
from binascii import unhexlify
import validators
import random
import string

from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField

from core.models import TZ_CHOICES

import automation


class Agent(models.Model):
    version = models.CharField(default="0.1.0", max_length=255)
    operating_system = models.CharField(null=True, max_length=255)
    plat = models.CharField(max_length=255, null=True)
    plat_release = models.CharField(max_length=255, null=True)
    hostname = models.CharField(max_length=255)
    local_ip = models.TextField(null=True)
    agent_id = models.CharField(max_length=200)
    last_seen = models.DateTimeField(null=True, blank=True)
    services = JSONField(null=True)
    public_ip = models.CharField(null=True, max_length=255)
    total_ram = models.IntegerField(null=True)
    used_ram = models.IntegerField(null=True)
    disks = JSONField(null=True)
    boot_time = models.FloatField(null=True)
    logged_in_username = models.CharField(null=True, max_length=200)
    client = models.CharField(max_length=200)
    antivirus = models.CharField(default="n/a", max_length=255)
    site = models.CharField(max_length=150)
    monitoring_type = models.CharField(max_length=30)
    description = models.CharField(null=True, max_length=255)
    mesh_node_id = models.CharField(null=True, max_length=255)
    overdue_email_alert = models.BooleanField(default=False)
    overdue_text_alert = models.BooleanField(default=False)
    overdue_time = models.PositiveIntegerField(default=30)
    uninstall_pending = models.BooleanField(default=False)
    uninstall_inprogress = models.BooleanField(default=False)
    check_interval = models.PositiveIntegerField(default=120)
    needs_reboot = models.BooleanField(default=False)
    managed_by_wsus = models.BooleanField(default=False)
    is_updating = models.BooleanField(default=False)
    choco_installed = models.BooleanField(default=False)
    wmi_detail = JSONField(null=True)
    policies_pending = models.BooleanField(default=False)
    time_zone = models.CharField(
        max_length=255, choices=TZ_CHOICES, null=True, blank=True
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
    def timezone(self):
        # return the default timezone unless the timezone is explicity set per agent
        if self.time_zone is not None:
            return self.time_zone
        else:
            from core.models import CoreSettings

            return CoreSettings.objects.first().default_time_zone

    @property
    def status(self):
        offline = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=4)
        overdue = dt.datetime.now(dt.timezone.utc) - dt.timedelta(
            minutes=self.overdue_time
        )

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

        if self.winupdates.filter(action="approve").exists():
            return True
        else:
            return False

    @property
    def salt_id(self):
        return f"{self.hostname}-{self.pk}"

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
        try:
            cpu = self.wmi_detail["cpu"][0]
            return [x["Name"] for x in cpu if "Name" in x][0]
        except:
            return "unknown cpu model"

    @property
    def local_ips(self):
        try:
            ips = self.wmi_detail["network_config"]
            ret = []
            for _ in ips:
                try:
                    addr = [x["IPAddress"] for x in _ if "IPAddress" in x][0]
                except:
                    continue
                else:
                    for ip in addr:
                        if validators.ipv4(ip):
                            ret.append(ip)

                if len(ret) == 1:
                    return ret[0]
                else:
                    return ", ".join(ret)
        except:
            return "error getting local ips"

    @property
    def make_model(self):
        try:
            comp_sys = self.wmi_detail["comp_sys"][0]
            comp_sys_prod = self.wmi_detail["comp_sys_prod"][0]
            make = [x["Vendor"] for x in comp_sys_prod if "Vendor" in x][0]
            model = [x["SystemFamily"] for x in comp_sys if "SystemFamily" in x][0]
            if not make or not model:
                return [x["Version"] for x in comp_sys_prod if "Version" in x][0]
            else:
                return f"{make} {model}"
        except:
            return "unknown make/model"

    @property
    def physical_disks(self):
        try:
            disks = self.wmi_detail["disk"]
            phys = []
            for disk in disks:
                model = [x["Caption"] for x in disk if "Caption" in x][0]
                size = [x["Size"] for x in disk if "Size" in x][0]
                interface_type = [
                    x["InterfaceType"] for x in disk if "InterfaceType" in x
                ][0]
                phys.append(
                    {
                        "model": model,
                        "size": round(int(size) / 1_073_741_824),  # bytes to GB
                        "interfaceType": interface_type,
                    }
                )

            return phys
        except:
            return [{"model": "unknown", "size": "unknown", "interfaceType": "unknown"}]


    def generate_checks_from_policies(self):
        # Clear agent checks managed by policy
        self.agentchecks.filter(managed_by_policy=True).delete()

        # Clear agent checks that have overriden_by_policy set
        self.agentchecks.update(overriden_by_policy=False)

        # Generate checks based on policies
        automation.models.Policy.generate_policy_checks(self)

        # Set policies_pending to false to disable policy generation on next checkin
        self.policies_pending = False
        self.save()

    # https://github.com/Ylianst/MeshCentral/issues/59#issuecomment-521965347
    def get_login_token(self, key, user, action=3):
        key = bytes.fromhex(key)
        key1 = key[0:48]
        key2 = key[48:]
        msg = '{{"a":{}, "u":"{}","time":{}}}'.format(action, user, int(time.time()))
        iv = secrets.token_bytes(16)

        # sha
        h = hashlib.sha3_384()
        h.update(key1)
        msg = h.digest() + msg.encode()

        # aes
        a = AES.new(key2, AES.MODE_CBC, iv)
        n = 16 - (len(msg) % 16)
        n = 16 if n == 0 else n
        pad = unhexlify("%02x" % n)
        msg = a.encrypt(msg + pad * n)

        return base64.b64encode(iv + msg, altchars=b"@$").decode("utf-8")

    @staticmethod
    def salt_api_cmd(**kwargs):
        try:
            salt_timeout = kwargs["salt_timeout"]
        except KeyError:
            salt_timeout = 60
        json = {
            "client": "local",
            "tgt": kwargs["hostname"],
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
        resp = requests.post(
            "http://" + settings.SALT_HOST + ":8123/run",
            json=[json],
            timeout=kwargs["timeout"],
        )
        return resp

    @staticmethod
    def salt_api_async(**kwargs):

        json = {
            "client": "local_async",
            "tgt": kwargs["hostname"],
            "fun": kwargs["func"],
            "username": settings.SALT_USERNAME,
            "password": settings.SALT_PASSWORD,
            "eauth": "pam",
        }

        if "arg" in kwargs:
            json.update({"arg": kwargs["arg"]})
        if "kwargs" in kwargs:
            json.update({"kwarg": kwargs["kwargs"]})
        resp = requests.post("http://" + settings.SALT_HOST + ":8123/run", json=[json])
        return resp

    @staticmethod
    def salt_api_job(jid):

        session = requests.Session()
        session.post(
            "http://" + settings.SALT_HOST + ":8123/login",
            json={
                "username": settings.SALT_USERNAME,
                "password": settings.SALT_PASSWORD,
                "eauth": "pam",
            },
        )

        return session.get(f"http://{settings.SALT_HOST}:8123/jobs/{jid}")

    @staticmethod
    def get_github_versions():
        r = requests.get("https://api.github.com/repos/wh1te909/winagent/releases")
        versions = {}
        for i, release in enumerate(r.json()):
            versions[i] = release["name"]

        return {"versions": versions, "data": r.json()}

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

        try:
            r = self.salt_api_cmd(
                hostname=self.salt_id,
                timeout=20,
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
        except Exception:
            return {"ret": False, "msg": "Unable to contact the agent"}

        salt_resp = r.json()["return"][0][self.salt_id]

        if isinstance(salt_resp, bool) and salt_resp == True:
            from logs.models import PendingAction

            details = {
                "taskname": task_name,
                "time": str(obj),
            }
            PendingAction(agent=self, action_type="schedreboot", details=details).save()

            nice_time = dt.datetime.strftime(obj, "%B %d, %Y at %I:%M %p")
            return {
                "ret": True,
                "msg": {"time": nice_time, "agent": self.hostname},
                "success": True,
            }

        elif isinstance(salt_resp, bool) and salt_resp == False:
            return {
                "ret": True,
                "msg": "Unable to create task (possibly because date/time cannot be in the past)",
                "success": False,
            }

        else:
            return {"ret": True, "msg": salt_resp, "success": False}

    def create_fix_salt_task(self):
        # https://github.com/wh1te909/winagent/commit/64bc96c131dbdb568e8552c85ed970d06af055df
        r = self.salt_api_cmd(
            hostname=self.salt_id,
            timeout=30,
            func="task.create_task",
            arg=[
                f"name=TacticalRMM_fixsalt",
                "force=True",
                "action_type=Execute",
                'cmd="C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"',
                'arguments="-m fixsalt"',
                "trigger_type=Daily",
                "start_time='10:30'",
                "repeat_interval='1 hour'",
                "ac_only=False",
                "stop_if_on_batteries=False",
            ],
        )

        try:
            data = r.json()
        except:
            return False
        else:
            ret = data["return"][0][self.salt_id]
            if isinstance(ret, bool) and ret:
                return True
            else:
                return False


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
            f"{self.agent.client}, {self.agent.site}, {self.agent.hostname} - data overdue",
            (
                f"Data has not been received from client {self.agent.client}, "
                f"site {self.agent.site}, "
                f"agent {self.agent.hostname} "
                "within the expected time."
            ),
        )

    def send_recovery_email(self):
        from core.models import CoreSettings

        CORE = CoreSettings.objects.first()
        CORE.send_mail(
            f"{self.agent.client}, {self.agent.site}, {self.agent.hostname} - data received",
            (
                f"Data has been received from client {self.agent.client}, "
                f"site {self.agent.site}, "
                f"agent {self.agent.hostname} "
                "after an interruption in data transmission."
            ),
        )

    def __str__(self):
        return self.agent.hostname
