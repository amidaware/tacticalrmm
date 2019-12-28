import validators
from statistics import mean

from django.db import models
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.postgres.fields import ArrayField

from agents.models import Agent

STANDARD_CHECK_CHOICES = [
    ("diskspace", "Disk Space Check"),
    ("ping", "Ping Check"),
    ("cpuload", "CPU Load Check"),
    ("memory", "Memory Check"),
    ("winsvc", "Win Service Check"),
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
        Agent, related_name="diskchecks", on_delete=models.CASCADE
    )
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="diskspace"
    )
    disk = models.CharField(max_length=2, null=True, blank=True)
    threshold = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    more_info = models.TextField(null=True, blank=True)
    last_run = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.agent.hostname} - {self.disk}"

    def send_email(self):
        percent_used = self.agent.disks[self.disk]["percent"]
        percent_free = 100 - percent_used
        send_mail(
            f"Disk Space Check Failing on {self.agent.hostname}",
            f"{self.agent.hostname} is failing disk space check {self.disk} - Free: {percent_free}%, Threshold: {self.threshold}%",
            settings.EMAIL_HOST_USER,
            settings.EMAIL_ALERT_RECIPIENTS,
            fail_silently=False,
        )


class DiskCheckEmail(models.Model):
    email = models.ForeignKey(DiskCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email.agent.hostname


class PingCheck(models.Model):
    agent = models.ForeignKey(
        Agent, related_name="pingchecks", on_delete=models.CASCADE
    )
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="ping"
    )
    ip = models.CharField(max_length=255)
    name = models.CharField(max_length=255, null=True, blank=True)
    failures = models.PositiveIntegerField(default=5)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    failure_count = models.IntegerField(default=0)
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    more_info = models.TextField(null=True, blank=True)
    last_run = models.DateTimeField(auto_now=True)

    def send_email(self):
        send_mail(
            f"Ping Check Fail on {self.agent.hostname}",
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
        return self.agent.hostname


class PingCheckEmail(models.Model):
    email = models.ForeignKey(PingCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email.agent.hostname


class CpuLoadCheck(models.Model):
    agent = models.ForeignKey(
        Agent, related_name="cpuloadchecks", on_delete=models.CASCADE
    )
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="cpuload"
    )
    cpuload = models.PositiveIntegerField(default=85)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    more_info = models.TextField(null=True, blank=True)
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    last_run = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.agent.hostname

    def send_email(self):

        cpuhistory = CpuHistory.objects.get(agent=self.agent).cpu_history
        avg = int(mean(cpuhistory))

        send_mail(
            f"CPU Load Check fail on {self.agent.hostname}",
            f"Average cpu utilization is {avg}% which is greater than the threshold {self.cpuload}%",
            settings.EMAIL_HOST_USER,
            settings.EMAIL_ALERT_RECIPIENTS,
            fail_silently=False,
        )


class CpuHistory(models.Model):
    agent = models.ForeignKey(
        Agent, related_name="cpuhistory", on_delete=models.CASCADE
    )
    cpu_history = ArrayField(models.IntegerField(blank=True), null=True, default=list)

    def __str__(self):
        return self.agent.hostname

    def format_nice(self):
        return ", ".join(str(f"{x}%") for x in self.cpu_history[-6:])


class CpuLoadCheckEmail(models.Model):
    email = models.ForeignKey(CpuLoadCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email.agent.hostname


class MemCheck(models.Model):
    agent = models.ForeignKey(Agent, related_name="memchecks", on_delete=models.CASCADE)
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="memory"
    )
    threshold = models.PositiveIntegerField(default=75)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    more_info = models.TextField(null=True, blank=True)
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    last_run = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.agent.hostname

    def send_email(self):

        memhistory = MemoryHistory.objects.get(agent=self.agent).mem_history
        avg = int(mean(memhistory))

        send_mail(
            f"Memory Check fail on {self.agent.hostname}",
            f"Average memory usage is {avg}% which is greater than the threshold {self.threshold}%",
            settings.EMAIL_HOST_USER,
            settings.EMAIL_ALERT_RECIPIENTS,
            fail_silently=False,
        )


class MemoryHistory(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    mem_history = ArrayField(models.IntegerField(blank=True), null=True, default=list)

    def __str__(self):
        return self.agent.hostname

    def format_nice(self):
        return ", ".join(str(f"{x}%") for x in self.mem_history[-6:])


class MemCheckEmail(models.Model):
    email = models.ForeignKey(MemCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email.agent.hostname


class WinServiceCheck(models.Model):
    agent = models.ForeignKey(
        Agent, related_name="winservicechecks", on_delete=models.CASCADE
    )
    check_type = models.CharField(
        max_length=30, choices=STANDARD_CHECK_CHOICES, default="winsvc"
    )
    svc_name = models.CharField(max_length=255)
    svc_display_name = models.CharField(max_length=255)
    pass_if_start_pending = models.BooleanField(default=False)
    restart_if_stopped = models.BooleanField(default=False)
    failures = models.PositiveIntegerField(default=1)
    failure_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=30, choices=CHECK_STATUS_CHOICES, default="pending"
    )
    more_info = models.TextField(null=True, blank=True)
    email_alert = models.BooleanField(default=False)
    text_alert = models.BooleanField(default=False)
    last_run = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.agent.hostname} - {self.svc_display_name}"

    def send_email(self):

        status = list(
            filter(lambda x: x["name"] == self.svc_name, self.agent.services)
        )[0]["status"]

        send_mail(
            f"Windows Service Check fail on {self.agent.hostname}",
            f"Service: {self.svc_display_name} - Status: {status.upper()}",
            settings.EMAIL_HOST_USER,
            settings.EMAIL_ALERT_RECIPIENTS,
            fail_silently=False,
        )


class WinServiceCheckEmail(models.Model):
    email = models.ForeignKey(WinServiceCheck, on_delete=models.CASCADE)
    sent = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email.agent.hostname} - {self.email.svc_display_name}"
