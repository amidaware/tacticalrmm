import random
import string

from django.test import TestCase, override_settings
from django.utils import timezone as djangotime

from rest_framework.test import APIClient
from rest_framework.test import force_authenticate
from rest_framework.authtoken.models import Token

from accounts.models import User
from agents.models import Agent
from winupdate.models import WinUpdatePolicy
from clients.models import Client, Site
from automation.models import Policy
from core.models import CoreSettings
from checks.models import Check
from autotasks.models import AutomatedTask


class PlainTestCase(TestCase):

    def authenticate(self):
        self.john = User(username="john")
        self.john.set_password("password")
        self.john.save()
        self.client = APIClient()
        self.client.force_authenticate(user=self.john)

    # fixes tests waiting 2 minutes for mesh token to appear
    @override_settings(MESH_TOKEN_KEY="123456")
    def setup_coresettings(self):
        self.coresettings = CoreSettings.objects.create()

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


class BaseTestCase(TestCase):
    def setUp(self):

        self.john = User(username="john")
        self.john.set_password("password")
        self.john.save()
        self.client = APIClient()
        self.client.force_authenticate(user=self.john)

        self.coresettings = CoreSettings.objects.create()
        self.agent = self.create_agent("DESKTOP-TEST123", "Google", "Main Office")
        self.agent_user = User.objects.create_user(
            username=self.agent.agent_id, password=User.objects.make_random_password(60)
        )
        self.agent_token = Token.objects.create(user=self.agent_user)
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
            name="testpolicy",
            desc="my awesome policy",
            active=True,
        )
        self.policy.server_clients.add(google)
        self.policy.workstation_clients.add(facebook)

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

        self.policyTask = AutomatedTask.objects.create(
            policy=self.policy, name="Test Task"
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

    def create_agent(self, hostname, client, site, monitoring_type="server"):
        return Agent.objects.create(
            operating_system="Windows 10",
            plat="windows",
            plat_release="windows-Server2019",
            hostname=f"{hostname}",
            salt_id=self.generate_agent_id(hostname),
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
            client=f"{client}",
            site=f"{site}",
            monitoring_type=monitoring_type,
            description="Test PC",
            mesh_node_id="abcdefghijklmnopAABBCCDD77443355##!!AI%@#$%#*",
            last_seen=djangotime.now(),
        )

    def generate_agents(
        self, numOfAgents, numOfClients, numOfSites, monitoring_type="server"
    ):

        agents = list()

        for c in range(numOfClients):
            client = Client.objects.create(client=f"Client{c}")

            for s in range(numOfSites):
                site = Site.objects.create(client=client, site=f"Site{s}")

                for a in range(numOfAgents):

                    agents.append(
                        self.create_agent(
                            f"Agent{a}", f"Client{c}", f"Site{s}", monitoring_type
                        )
                    )

        return agents

    def generate_agent_id(self, hostname):
        rand = "".join(random.choice(string.ascii_letters) for _ in range(35))
        return f"{rand}-{hostname}"
