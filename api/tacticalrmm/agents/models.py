import requests

""" import salt.client
import salt.config
import salt.wheel

opts = salt.config.master_config("/etc/salt/master")
wheel = salt.wheel.WheelClient(opts)
local = salt.client.LocalClient() """


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
    cpu_load = models.FloatField(null=True)
    total_ram = models.IntegerField(null=True)
    used_ram = models.IntegerField(null=True)
    disks = JSONField(null=True)
    boot_time = models.FloatField(null=True)
    logged_in_username = models.CharField(null=True, max_length=200)
    cpu_info = JSONField(null=True)
    client = models.CharField(max_length=200)
    antivirus = models.CharField(default="n/a", max_length=255)
    site = models.CharField(max_length=150)
    monitoring_type = models.CharField(max_length=30)
    description = models.CharField(null=True, max_length=255)
    mesh_node_id = models.CharField(null=True, max_length=255)
    overdue_email_alert = models.BooleanField(default=False)
    overdue_text_alert = models.BooleanField(default=False)
    overdue_time = models.PositiveIntegerField(default=30)
    status = models.CharField(default="n/a", max_length=30)
    uninstall_pending = models.BooleanField(default=False)
    uninstall_inprogress = models.BooleanField(default=False)
    ping_check_interval = models.PositiveIntegerField(default=300)
    needs_reboot = models.BooleanField(default=False)
    managed_by_wsus = models.BooleanField(default=False)
    is_updating = models.BooleanField(default=False)

    def __str__(self):
        return self.hostname

    @property
    def has_patches_pending(self):
        from winupdate.models import WinUpdate

        if WinUpdate.objects.filter(agent=self).filter(action="approve").exists():
            return True

        return False

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
            "http://127.0.0.1:8123/run", json=[json], timeout=kwargs["timeout"]
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
        resp = requests.post("http://127.0.0.1:8123/run", json=[json])
        return resp

    @staticmethod
    def salt_api_job(jid):

        session = requests.Session()
        session.post(
            "http://127.0.0.1:8123/login",
            json={
                "username": settings.SALT_USERNAME,
                "password": settings.SALT_PASSWORD,
                "eauth": "pam",
            },
        )

        return session.get(f"http://127.0.0.1:8123/jobs/{jid}")

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

