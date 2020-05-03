import requests
import datetime
from datetime import timezone
import time
import hashlib
import secrets
import base64
from Crypto.Cipher import AES
from binascii import unhexlify
import validators

from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField


class Agent(models.Model):
    version = models.CharField(default="0.1.0", max_length=255)
    operating_system = models.CharField(null=True, max_length=255)
    plat = models.CharField(max_length=255, null=True)
    plat_release = models.CharField(max_length=255, null=True)
    hostname = models.CharField(max_length=255)
    local_ip = models.TextField(null=True)
    agent_id = models.CharField(max_length=200)
    last_seen = models.DateTimeField(auto_now=True)
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

    def __str__(self):
        return self.hostname

    @property
    def status(self):
        offline = datetime.datetime.now(timezone.utc) - datetime.timedelta(minutes=4)
        overdue = datetime.datetime.now(timezone.utc) - datetime.timedelta(
            minutes=self.overdue_time
        )
        if (self.last_seen < offline) and (self.last_seen > overdue):
            return "offline"
        elif (self.last_seen < offline) and (self.last_seen < overdue):
            return "overdue"
        else:
            return "online"

    @property
    def has_patches_pending(self):
        from winupdate.models import WinUpdate

        if WinUpdate.objects.filter(agent=self).filter(action="approve").exists():
            return True

        return False

    @property
    def salt_id(self):
        return f"{self.hostname}-{self.pk}"

    @property
    def has_failing_checks(self):

        checks = (
            "diskchecks",
            "scriptchecks",
            "pingchecks",
            "cpuloadchecks",
            "memchecks",
            "winservicechecks",
        )

        for check in checks:
            obj = getattr(self, check)
            if obj.exists():
                for i in obj.all():
                    if i.status == "failing":
                        return True

        return False

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

    """ @staticmethod
    def salt_cmd(tgt, fun, arg=[], timeout=60, kwargs={}):
        return local.cmd(
            tgt, 
            fun, 
            arg, 
            timeout=timeout, 
            tgt_type="glob", 
            ret="", 
            jid="", 
            full_return=False, 
            kwarg=kwargs, 
            username=settings.SALT_USERNAME, 
            password=settings.SALT_PASSWORD, 
            eauth="pam"
        )
    
    @staticmethod
    def salt_wheel_cmd(hostname, func):
        resp = wheel.cmd_sync({
            "fun": func,
            "match": hostname,
            "username": settings.SALT_USERNAME,
            "password": settings.SALT_PASSWORD,
            "eauth": "pam"
        }, timeout=100)

        return resp """
