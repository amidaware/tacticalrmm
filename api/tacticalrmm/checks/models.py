import validators
from statistics import mean
import datetime as dt
import string


from django.utils import timezone as djangotime
from django.db import models
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.postgres.fields import ArrayField

from agents.models import Agent
from automation.models import Policy

STANDARD_CHECK_CHOICES = [
    ("diskspace", "Disk Space Check"),
    ("ping", "Ping Check"),
    ("cpuload", "CPU Load Check"),
    ("memory", "Memory Check"),
    ("winsvc", "Win Service Check"),
    ("script", "Script Check"),
]

SCRIPT_CHECK_SHELLS = [
    ("powershell", "Powershell"),
    ("cmd", "Batch (CMD)"),
    ("python", "Python"),
]

CHECK_STATUS_CHOICES = [
    ("passing", "Passing"),
    ("failing", "Failing"),
    ("pending", "Pending"),
]


def validate_threshold(threshold):
    try:
        int(threshold)
    except ValueError:
        return False

    if int(threshold) <= 0 or int(threshold) >= 100:
        return False

    return True


class DiskCheck(models.Model):
    agent = models.ForeignKey(
        Agent,
        related_name="diskchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="diskspace"
    )
    policy = models.ForeignKey(
        Policy,
        related_name="diskchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    disk = models.CharField(max_length=2, null=True, blank=True)
    threshold = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    more_info = models.TextField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    failures = models.PositiveIntegerField(default=5)
    failure_count = models.PositiveIntegerField(default=0)
    task_on_failure = models.ForeignKey(
        "automation.AutomatedTask",
        null=True,
        blank=True,
        related_name="disktaskfailure",
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        if self.agent:
            return f"{self.agent.hostname} - {self.disk}"
        else:
            return self.policy.name

    @property
    def readable_desc(self):
        return f"Disk space check: Drive {self.disk}"

    @property
    def assigned_task(self):
        return self.task_on_failure.name

    def handle_check(self, data):
        if data["status"] == "passing" and self.failure_count != 0:
            self.failure_count = 0
            self.save(update_fields=["failure_count"])
        elif data["status"] == "failing":
            self.failure_count += 1
            self.save(update_fields=["failure_count"])
            if self.email_alert and self.failure_count >= self.failures:
                from .tasks import handle_check_email_alert_task

                handle_check_email_alert_task.delay("diskspace", self.pk)

    def send_email(self):
        percent_used = self.agent.disks[self.disk]["percent"]
        percent_free = 100 - percent_used
        send_mail(
            f"Disk Space Check Failing on {self}",
            f"{self} is failing disk space check {self.disk} - Free: {percent_free}%, Threshold: {self.threshold}%",
            settings.EMAIL_HOST_USER,
            settings.EMAIL_ALERT_RECIPIENTS,
            fail_silently=False,
        )

    @staticmethod
    def all_disks():
        return [f"{disk}:" for disk in string.ascii_uppercase]


class DiskCheckEmail(models.Model):
    email = models.ForeignKey(DiskCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.email.agent:
            return self.email.agent.hostname
        else:
            return self.email.policy.name


class Script(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    filename = models.CharField(max_length=255)
    shell = models.CharField(
        max_length=100, choices=SCRIPT_CHECK_SHELLS, default="powershell"
    )

    @property
    def filepath(self):
        return f"salt://scripts//userdefined//{self.filename}"

    @property
    def file(self):
        return f"/srv/salt/scripts/userdefined/{self.filename}"

    @staticmethod
    def validate_filename(filename):
        if (
            not filename.endswith(".py")
            and not filename.endswith(".ps1")
            and not filename.endswith(".bat")
        ):
            return False

        return True

    def __str__(self):
        return self.filename


class ScriptCheck(models.Model):
    agent = models.ForeignKey(
        Agent,
        related_name="scriptchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="script"
    )
    policy = models.ForeignKey(
        Policy,
        related_name="scriptchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    timeout = models.PositiveIntegerField(default=120)
    failures = models.PositiveIntegerField(default=5)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    failure_count = models.PositiveIntegerField(default=0)
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    retcode = models.IntegerField(default=0)
    execution_time = models.CharField(max_length=100, default="0.0000")
    last_run = models.DateTimeField(null=True, blank=True)
    script = models.ForeignKey(Script, related_name="script", on_delete=models.CASCADE)
    task_on_failure = models.ForeignKey(
        "automation.AutomatedTask",
        null=True,
        blank=True,
        related_name="scripttaskfailure",
        on_delete=models.SET_NULL,
    )

    @property
    def readable_desc(self):
        return f"Script check: {self.script.name}"

    @property
    def assigned_task(self):
        return self.task_on_failure.name

    def handle_check(self, data):
        if data["status"] == "passing" and self.failure_count != 0:
            self.failure_count = 0
            self.save(update_fields=["failure_count"])
        elif data["status"] == "failing":
            self.failure_count += 1
            self.save(update_fields=["failure_count"])
            if self.email_alert and self.failure_count >= self.failures:
                from .tasks import handle_check_email_alert_task

                handle_check_email_alert_task.delay("script", self.pk)

    def send_email(self):
        send_mail(
            f"Script Check Fail on {self}",
            f"Script check {self.script.name} is failing on {self}",
            settings.EMAIL_HOST_USER,
            settings.EMAIL_ALERT_RECIPIENTS,
            fail_silently=False,
        )

    def __str__(self):
        if self.agent:
            return f"{self.agent.hostname} - {self.script.filename}"
        else:
            return self.policy.name


class ScriptCheckEmail(models.Model):
    email = models.ForeignKey(ScriptCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.email.agent:
            return self.email.agent.hostname
        else:
            return self.email.policy.name


class PingCheck(models.Model):
    agent = models.ForeignKey(
        Agent,
        related_name="pingchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="ping"
    )
    policy = models.ForeignKey(
        Policy,
        related_name="pingchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    ip = models.CharField(max_length=255)
    name = models.CharField(max_length=255, null=True, blank=True)
    failures = models.PositiveIntegerField(default=5)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    failure_count = models.PositiveIntegerField(default=0)
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    more_info = models.TextField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    task_on_failure = models.ForeignKey(
        "automation.AutomatedTask",
        null=True,
        blank=True,
        related_name="pingtaskfailure",
        on_delete=models.SET_NULL,
    )

    @property
    def readable_desc(self):
        return f"Ping check: {self.name}"

    @property
    def assigned_task(self):
        return self.task_on_failure.name

    def handle_check(self, data):
        if data["status"] == "passing" and self.failure_count != 0:
            self.failure_count = 0
            self.save(update_fields=["failure_count"])
        elif data["status"] == "failing":
            self.failure_count += 1
            self.save(update_fields=["failure_count"])
            if self.email_alert and self.failure_count >= self.failures:
                from .tasks import handle_check_email_alert_task

                handle_check_email_alert_task.delay("ping", self.pk)

    def send_email(self):
        send_mail(
            f"Ping Check Fail on {self}",
            f"Ping check {self.name} ({self.ip}) is failing",
            settings.EMAIL_HOST_USER,
            settings.EMAIL_ALERT_RECIPIENTS,
            fail_silently=False,
        )

    @staticmethod
    def validate_hostname_or_ip(i):
        if validators.ipv4(i) or validators.ipv6(i) or validators.domain(i):
            return True
        return False

    def __str__(self):
        if self.agent:
            return self.agent.hostname
        else:
            return self.policy.name


class PingCheckEmail(models.Model):
    email = models.ForeignKey(PingCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.email.agent:
            return self.email.agent.hostname
        else:
            return self.email.policy.name


class CpuLoadCheck(models.Model):
    agent = models.ForeignKey(
        Agent,
        related_name="cpuloadchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="cpuload"
    )
    policy = models.ForeignKey(
        Policy,
        related_name="cpuloadchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    cpuload = models.PositiveIntegerField(default=85)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    last_run = models.DateTimeField(null=True, blank=True)
    failures = models.PositiveIntegerField(default=5)
    failure_count = models.PositiveIntegerField(default=0)
    history = ArrayField(models.IntegerField(blank=True), null=True, default=list)
    task_on_failure = models.ForeignKey(
        "automation.AutomatedTask",
        null=True,
        blank=True,
        related_name="cpuloadtaskfailure",
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        if self.agent:
            return self.agent.hostname
        else:
            return self.policy.name

    @property
    def more_info(self):
        return ", ".join(str(f"{x}%") for x in self.history[-6:])

    @property
    def readable_desc(self):
        return f"CPU Load check: > {self.cpuload}%"

    @property
    def assigned_task(self):
        return self.task_on_failure.name

    def handle_check(self, data):
        if len(self.history) < 15:
            self.history.append(data["cpu_load"])
        else:
            self.history.append(data["cpu_load"])
            self.history = self.history[-15:]

        self.last_run = dt.datetime.now(tz=djangotime.utc)
        self.save(update_fields=["history", "last_run"])

        avg = int(mean(self.history))
        if avg > self.cpuload:
            self.status = "failing"
            self.failure_count += 1
            self.save(update_fields=["status", "failure_count"])
        else:
            self.status = "passing"
            if self.failure_count != 0:
                self.failure_count = 0
                self.save(update_fields=["status", "failure_count"])
            else:
                self.save(update_fields=["status"])

        if self.email_alert and self.failure_count >= self.failures:
            from .tasks import handle_check_email_alert_task

            handle_check_email_alert_task.delay("cpuload", self.pk)

    def send_email(self):

        send_mail(
            f"CPU Load Check fail on {self}",
            f"Average cpu utilization is {int(mean(self.history))}% which is greater than the threshold {self.cpuload}%",
            settings.EMAIL_HOST_USER,
            settings.EMAIL_ALERT_RECIPIENTS,
            fail_silently=False,
        )


class CpuLoadCheckEmail(models.Model):
    email = models.ForeignKey(CpuLoadCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.email.agent:
            return self.email.agent.hostname
        else:
            return self.email.policy.name


class MemCheck(models.Model):
    agent = models.ForeignKey(
        Agent, related_name="memchecks", null=True, blank=True, on_delete=models.CASCADE
    )
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="memory"
    )
    policy = models.ForeignKey(
        Policy,
        related_name="memchecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    threshold = models.PositiveIntegerField(default=75)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    last_run = models.DateTimeField(null=True, blank=True)
    failures = models.PositiveIntegerField(default=5)
    failure_count = models.PositiveIntegerField(default=0)
    history = ArrayField(models.IntegerField(blank=True), null=True, default=list)
    task_on_failure = models.ForeignKey(
        "automation.AutomatedTask",
        null=True,
        blank=True,
        related_name="memtaskfailure",
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        if self.agent:
            return self.agent.hostname
        else:
            return self.policy.name

    @property
    def more_info(self):
        return ", ".join(str(f"{x}%") for x in self.history[-6:])

    @property
    def readable_desc(self):
        return f"Memory check: > {self.threshold}%"

    @property
    def assigned_task(self):
        return self.task_on_failure.name

    def handle_check(self, data):
        if len(self.history) < 15:
            self.history.append(data["used_ram"])
        else:
            self.history.append(data["used_ram"])
            self.history = self.history[-15:]

        self.last_run = dt.datetime.now(tz=djangotime.utc)
        self.save(update_fields=["history", "last_run"])

        avg = int(mean(self.history))
        if avg > self.threshold:
            self.status = "failing"
            self.failure_count += 1
            self.save(update_fields=["status", "failure_count"])
        else:
            self.status = "passing"
            if self.failure_count != 0:
                self.failure_count = 0
                self.save(update_fields=["status", "failure_count"])
            else:
                self.save(update_fields=["status"])

        if self.email_alert and self.failure_count >= self.failures:
            from .tasks import handle_check_email_alert_task

            handle_check_email_alert_task.delay("memory", self.pk)

    def send_email(self):

        send_mail(
            f"Memory Check fail on {self}",
            f"Average memory usage is {int(mean(self.history))}% which is greater than the threshold {self.threshold}%",
            settings.EMAIL_HOST_USER,
            settings.EMAIL_ALERT_RECIPIENTS,
            fail_silently=False,
        )


class MemCheckEmail(models.Model):
    email = models.ForeignKey(MemCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.email.agent:
            return self.email.agent.hostname
        else:
            return self.email.policy.name


class WinServiceCheck(models.Model):
    agent = models.ForeignKey(
        Agent,
        related_name="winservicechecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="winsvc"
    )
    policy = models.ForeignKey(
        Policy,
        related_name="winservicechecks",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    svc_name = models.CharField(max_length=255)
    svc_display_name = models.CharField(max_length=255)
    pass_if_start_pending = models.BooleanField(default=False)
    restart_if_stopped = models.BooleanField(default=False)
    failures = models.PositiveIntegerField(default=1)
    failure_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    more_info = models.TextField(null=True, blank=True)
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    last_run = models.DateTimeField(null=True, blank=True)
    task_on_failure = models.ForeignKey(
        "automation.AutomatedTask",
        null=True,
        blank=True,
        related_name="winsvctaskfailure",
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        if self.agent:
            return f"{self.agent.hostname} - {self.svc_display_name}"
        else:
            return self.policy.name

    @property
    def readable_desc(self):
        return f"Service check: {self.svc_display_name}"

    @property
    def assigned_task(self):
        return self.task_on_failure.name

    def handle_check(self, data):
        if data["status"] == "passing" and self.failure_count != 0:
            self.failure_count = 0
            self.save(update_fields=["failure_count"])
        elif data["status"] == "failing":
            self.failure_count += 1
            self.save(update_fields=["failure_count"])
            if self.email_alert and self.failure_count >= self.failures:
                from .tasks import handle_check_email_alert_task

                handle_check_email_alert_task.delay("winsvc", self.pk)

    def send_email(self):

        status = list(
            filter(lambda x: x["name"] == self.svc_name, self.agent.services)
        )[0]["status"]

        send_mail(
            f"Windows Service Check fail on {self}",
            f"Service: {self.svc_display_name} - Status: {status.upper()}",
            settings.EMAIL_HOST_USER,
            settings.EMAIL_ALERT_RECIPIENTS,
            fail_silently=False,
        )


class WinServiceCheckEmail(models.Model):
    email = models.ForeignKey(WinServiceCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.email.agent:
            return f"{self.email.agent.hostname} - {self.email.svc_display_name}"
        else:
            return self.email.policy.name
