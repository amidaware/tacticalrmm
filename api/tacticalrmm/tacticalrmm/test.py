from django.test import TestCase
from django.utils import timezone as djangotime

from unittest.mock import patch

from rest_framework.test import APIClient
from rest_framework.test import force_authenticate

from accounts.models import User
from agents.models import Agent
from winupdate.models import WinUpdatePolicy
from clients.models import Client, Site
from automation.models import Policy
from core.models import CoreSettings
from checks.models import Check


class BaseTestCase(TestCase):
    def setUp(self):

        self.john = User(username="john")
        self.john.set_password("password")
        self.john.save()
        self.client = APIClient()
        self.client.force_authenticate(user=self.john)

        self.coresettings = CoreSettings.objects.create()

        self.agent = Agent.objects.create(
            operating_system="Windows 10",
            plat="windows",
            plat_release="windows-Server2019",
            hostname="DESKTOP-TEST123",
            local_ip="10.0.25.188",
            agent_id="71AHC-AA813-HH1BC-AAHH5-00013|DESKTOP-TEST123",
            services=[
                {
                    "pid": 880,
                    "name": "AeLookupSvc",
                    "status": "stopped",
                    "binpath": "C:\\Windows\\system32\\svchost.exe -k netsvcs",
                    "username": "localSystem",
                    "start_type": "manual",
                    "description": "Processes application compatibility cache requests for applications as they are launched",
                    "display_name": "Application Experience",
                },
                {
                    "pid": 812,
                    "name": "ALG",
                    "status": "stopped",
                    "binpath": "C:\\Windows\\System32\\alg.exe",
                    "username": "NT AUTHORITY\\LocalService",
                    "start_type": "manual",
                    "description": "Provides support for 3rd party protocol plug-ins for Internet Connection Sharing",
                    "display_name": "Application Layer Gateway Service",
                },
            ],
            public_ip="74.13.24.14",
            total_ram=16,
            used_ram=33,
            disks={
                "C:": {
                    "free": "42.3G",
                    "used": "17.1G",
                    "total": "59.5G",
                    "device": "C:",
                    "fstype": "NTFS",
                    "percent": 28,
                }
            },
            boot_time=8173231.4,
            logged_in_username="John",
            client="Google",
            site="Main Office",
            monitoring_type="server",
            description="Test PC",
            mesh_node_id="abcdefghijklmnopAABBCCDD77443355##!!AI%@#$%#*",
            last_seen=djangotime.now(),
        )

        self.update_policy = WinUpdatePolicy.objects.create(agent=self.agent)

        Client.objects.create(client="Google")
        Client.objects.create(client="Facebook")
        google = Client.objects.get(client="Google")
        facebook = Client.objects.get(client="Facebook")
        Site.objects.create(client=google, site="Main Office")
        Site.objects.create(client=google, site="LA Office")
        Site.objects.create(client=google, site="MO Office")
        Site.objects.create(client=facebook, site="Main Office")
        Site.objects.create(client=facebook, site="NY Office")

        self.policy = Policy.objects.create(
            name="testpolicy", desc="my awesome policy", active=True,
        )
        self.policy.clients.add(google)
        self.policy.clients.add(facebook)

        self.agentDiskCheck = Check.objects.create(
            agent=self.agent,
            check_type="diskspace",
            disk="C:",
            threshold=41,
            fails_b4_alert=4,
        )
        self.policyDiskCheck = Check.objects.create(
            policy=self.policy,
            check_type="diskspace",
            disk="M:",
            threshold=87,
            fails_b4_alert=1,
        )

    def check_not_authenticated(self, method, url):
        self.client.logout()
        switch = {
            "get": self.client.get(url),
            "post": self.client.post(url),
            "put": self.client.put(url),
            "patch": self.client.patch(url),
            "delete": self.client.delete(url),
        }
        r = switch.get(method)
        self.assertEqual(r.status_code, 401)
