import json
import random
import string
import datetime as dt

from django.core.management.base import BaseCommand
from django.utils import timezone as djangotime
from django.conf import settings
from django.core.management import call_command

from accounts.models import User
from agents.models import Agent, AgentHistory
from clients.models import Client, Site
from software.models import InstalledSoftware
from winupdate.models import WinUpdate, WinUpdatePolicy
from checks.models import Check, CheckHistory
from scripts.models import Script
from autotasks.models import AutomatedTask
from automation.models import Policy
from logs.models import PendingAction, AuditLog

from tacticalrmm.demo_data import (
    disks,
    temp_dir_stdout,
    spooler_stdout,
    ping_fail_output,
    ping_success_output,
)

AGENTS_TO_GENERATE = 250

SVCS = settings.BASE_DIR.joinpath("tacticalrmm/test_data/winsvcs.json")
WMI_1 = settings.BASE_DIR.joinpath("tacticalrmm/test_data/wmi1.json")
WMI_2 = settings.BASE_DIR.joinpath("tacticalrmm/test_data/wmi2.json")
WMI_3 = settings.BASE_DIR.joinpath("tacticalrmm/test_data/wmi3.json")
SW_1 = settings.BASE_DIR.joinpath("tacticalrmm/test_data/software1.json")
SW_2 = settings.BASE_DIR.joinpath("tacticalrmm/test_data/software2.json")
WIN_UPDATES = settings.BASE_DIR.joinpath("tacticalrmm/test_data/winupdates.json")
EVT_LOG_FAIL = settings.BASE_DIR.joinpath(
    "tacticalrmm/test_data/eventlog_check_fail.json"
)


class Command(BaseCommand):
    help = "populate database with fake agents"

    def rand_string(self, length):
        chars = string.ascii_letters
        return "".join(random.choice(chars) for _ in range(length))

    def handle(self, *args, **kwargs):

        user = User.objects.first()
        user.totp_key = "ABSA234234"
        user.save(update_fields=["totp_key"])

        Client.objects.all().delete()
        Agent.objects.all().delete()
        Check.objects.all().delete()
        Script.objects.all().delete()
        AutomatedTask.objects.all().delete()
        CheckHistory.objects.all().delete()
        Policy.objects.all().delete()
        AuditLog.objects.all().delete()
        PendingAction.objects.all().delete()

        call_command("load_community_scripts")

        # policies
        check_policy = Policy()
        check_policy.name = "Demo Checks Policy"
        check_policy.desc = "Demo Checks Policy"
        check_policy.active = True
        check_policy.enforced = True
        check_policy.save()

        patch_policy = Policy()
        patch_policy.name = "Demo Patch Policy"
        patch_policy.desc = "Demo Patch Policy"
        patch_policy.active = True
        patch_policy.enforced = True
        patch_policy.save()

        update_policy = WinUpdatePolicy()
        update_policy.policy = patch_policy
        update_policy.critical = "approve"
        update_policy.important = "approve"
        update_policy.moderate = "approve"
        update_policy.low = "ignore"
        update_policy.other = "ignore"
        update_policy.run_time_days = [6, 0, 2]
        update_policy.run_time_day = 1
        update_policy.reboot_after_install = "required"
        update_policy.reprocess_failed = True
        update_policy.email_if_fail = True
        update_policy.save()

        clients = [
            "Company 2",
            "Company 3",
            "Company 1",
            "Company 4",
            "Company 5",
            "Company 6",
        ]
        sites1 = ["HQ1", "LA Office 1", "NY Office 1"]
        sites2 = ["HQ2", "LA Office 2", "NY Office 2"]
        sites3 = ["HQ3", "LA Office 3", "NY Office 3"]
        sites4 = ["HQ4", "LA Office 4", "NY Office 4"]
        sites5 = ["HQ5", "LA Office 5", "NY Office 5"]
        sites6 = ["HQ6", "LA Office 6", "NY Office 6"]

        client1 = Client(name="Company 1")
        client2 = Client(name="Company 2")
        client3 = Client(name="Company 3")
        client4 = Client(name="Company 4")
        client5 = Client(name="Company 5")
        client6 = Client(name="Company 6")

        client1.save()
        client2.save()
        client3.save()
        client4.save()
        client5.save()
        client6.save()

        for site in sites1:
            Site(client=client1, name=site).save()

        for site in sites2:
            Site(client=client2, name=site).save()

        for site in sites3:
            Site(client=client3, name=site).save()

        for site in sites4:
            Site(client=client4, name=site).save()

        for site in sites5:
            Site(client=client5, name=site).save()

        for site in sites6:
            Site(client=client6, name=site).save()

        hostnames = [
            "DC-1",
            "DC-2",
            "FSV-1",
            "FSV-2",
            "WSUS",
            "DESKTOP-12345",
            "LAPTOP-55443",
        ]
        descriptions = ["Bob's computer", "Primary DC", "File Server", "Karen's Laptop"]
        modes = ["server", "workstation"]
        op_systems_servers = [
            "Microsoft Windows Server 2016 Standard, 64bit (build 14393)",
            "Microsoft Windows Server 2012 R2 Standard, 64bit (build 9600)",
            "Microsoft Windows Server 2019 Standard, 64bit (build 17763)",
        ]

        op_systems_workstations = [
            "Microsoft Windows 8.1 Pro, 64bit (build 9600)",
            "Microsoft Windows 10 Pro for Workstations, 64bit (build 18363)",
            "Microsoft Windows 10 Pro, 64bit (build 18363)",
        ]

        public_ips = ["65.234.22.4", "74.123.43.5", "44.21.134.45"]

        total_rams = [4, 8, 16, 32, 64, 128]
        used_rams = [10, 13, 60, 25, 76, 34, 56, 34, 39]

        now = dt.datetime.now()

        boot_times = []

        for _ in range(15):
            rand_hour = now - dt.timedelta(hours=random.randint(1, 22))
            boot_times.append(str(rand_hour.timestamp()))

        for _ in range(5):
            rand_days = now - dt.timedelta(days=random.randint(2, 50))
            boot_times.append(str(rand_days.timestamp()))

        user_names = ["None", "Karen", "Steve", "jsmith", "jdoe"]

        with open(SVCS) as f:
            services = json.load(f)

        # WMI
        with open(WMI_1) as f:
            wmi1 = json.load(f)

        with open(WMI_2) as f:
            wmi2 = json.load(f)

        with open(WMI_3) as f:
            wmi3 = json.load(f)

        wmi_details = []
        wmi_details.append(wmi1)
        wmi_details.append(wmi2)
        wmi_details.append(wmi3)

        # software
        with open(SW_1) as f:
            software1 = json.load(f)

        with open(SW_2) as f:
            software2 = json.load(f)

        softwares = []
        softwares.append(software1)
        softwares.append(software2)

        # windows updates
        with open(WIN_UPDATES) as f:
            windows_updates = json.load(f)["samplecomputer"]

        # event log check fail data
        with open(EVT_LOG_FAIL) as f:
            eventlog_check_fail_data = json.load(f)

        # create scripts

        clear_spool = Script()
        clear_spool.name = "Clear Print Spooler"
        clear_spool.description = "clears the print spooler. Fuck printers"
        clear_spool.filename = "clear_print_spool.bat"
        clear_spool.shell = "cmd"
        clear_spool.save()

        check_net_aware = Script()
        check_net_aware.name = "Check Network Location Awareness"
        check_net_aware.description = "Check's network location awareness on domain computers, should always be domain profile and not public or private. Sometimes happens when computer restarts before domain available. This script will return 0 if check passes or 1 if it fails."
        check_net_aware.filename = "check_network_loc_aware.ps1"
        check_net_aware.shell = "powershell"
        check_net_aware.save()

        check_pool_health = Script()
        check_pool_health.name = "Check storage spool health"
        check_pool_health.description = "loops through all storage pools and will fail if any of them are not healthy"
        check_pool_health.filename = "check_storage_pool_health.ps1"
        check_pool_health.shell = "powershell"
        check_pool_health.save()

        restart_nla = Script()
        restart_nla.name = "Restart NLA Service"
        restart_nla.description = "restarts the Network Location Awareness windows service to fix the nic profile. Run this after the check network service fails"
        restart_nla.filename = "restart_nla.ps1"
        restart_nla.shell = "powershell"
        restart_nla.save()

        show_tmp_dir_script = Script()
        show_tmp_dir_script.name = "Check temp dir"
        show_tmp_dir_script.description = "shows files in temp dir using python"
        show_tmp_dir_script.filename = "show_temp_dir.py"
        show_tmp_dir_script.shell = "python"
        show_tmp_dir_script.save()

        for count_agents in range(AGENTS_TO_GENERATE):

            client = random.choice(clients)

            if client == "Company 1":
                site = random.choice(sites1)
            elif client == "Company 2":
                site = random.choice(sites2)
            elif client == "Company 3":
                site = random.choice(sites3)
            elif client == "Company 4":
                site = random.choice(sites4)
            elif client == "Company 5":
                site = random.choice(sites5)
            elif client == "Company 6":
                site = random.choice(sites6)

            agent = Agent()

            mode = random.choice(modes)
            if mode == "server":
                agent.operating_system = random.choice(op_systems_servers)
            else:
                agent.operating_system = random.choice(op_systems_workstations)

            agent.hostname = random.choice(hostnames)
            agent.version = settings.LATEST_AGENT_VER
            agent.salt_ver = "1.1.0"
            agent.site = Site.objects.get(name=site)
            agent.agent_id = self.rand_string(25)
            agent.description = random.choice(descriptions)
            agent.monitoring_type = mode
            agent.public_ip = random.choice(public_ips)
            agent.last_seen = djangotime.now()
            agent.plat = "windows"
            agent.plat_release = "windows-2019Server"
            agent.total_ram = random.choice(total_rams)
            agent.used_ram = random.choice(used_rams)
            agent.boot_time = random.choice(boot_times)
            agent.logged_in_username = random.choice(user_names)
            agent.antivirus = "windowsdefender"
            agent.mesh_node_id = (
                "3UiLhe420@kaVQ0rswzBeonW$WY0xrFFUDBQlcYdXoriLXzvPmBpMrV99vRHXFlb"
            )
            agent.overdue_email_alert = random.choice([True, False])
            agent.overdue_text_alert = random.choice([True, False])
            agent.needs_reboot = random.choice([True, False])
            agent.wmi_detail = random.choice(wmi_details)
            agent.services = services
            agent.disks = random.choice(disks)
            agent.salt_id = "not-used"

            agent.save()

            InstalledSoftware(agent=agent, software=random.choice(softwares)).save()

            if mode == "workstation":
                WinUpdatePolicy(agent=agent, run_time_days=[5, 6]).save()
            else:
                WinUpdatePolicy(agent=agent).save()

            # windows updates load
            guids = []
            for k in windows_updates.keys():
                guids.append(k)

            for i in guids:
                WinUpdate(
                    agent=agent,
                    guid=i,
                    kb=windows_updates[i]["KBs"][0],
                    mandatory=windows_updates[i]["Mandatory"],
                    title=windows_updates[i]["Title"],
                    needs_reboot=windows_updates[i]["NeedsReboot"],
                    installed=windows_updates[i]["Installed"],
                    downloaded=windows_updates[i]["Downloaded"],
                    description=windows_updates[i]["Description"],
                    severity=windows_updates[i]["Severity"],
                ).save()

            # agent histories
            hist = AgentHistory()
            hist.agent = agent
            hist.type = "cmd_run"
            hist.command = "ping google.com"
            hist.username = "demo"
            hist.results = ping_success_output
            hist.save()

            hist1 = AgentHistory()
            hist1.agent = agent
            hist1.type = "script_run"
            hist1.script = clear_spool
            hist1.script_results = {
                "id": 1,
                "stderr": "",
                "stdout": spooler_stdout,
                "execution_time": 3.5554593,
                "retcode": 0,
            }
            hist1.save()

            # disk space check
            check1 = Check()
            check1.agent = agent
            check1.check_type = "diskspace"
            check1.status = "passing"
            check1.last_run = djangotime.now()
            check1.more_info = "Total: 498.7GB, Free: 287.4GB"
            check1.warning_threshold = 25
            check1.error_threshold = 10
            check1.disk = "C:"
            check1.email_alert = random.choice([True, False])
            check1.text_alert = random.choice([True, False])
            check1.save()

            for i in range(30):
                check1_history = CheckHistory()
                check1_history.check_id = check1.id
                check1_history.x = djangotime.now() - djangotime.timedelta(
                    minutes=i * 2
                )
                check1_history.y = random.randint(13, 40)
                check1_history.save()

            # ping check
            check2 = Check()
            check2.agent = agent
            check2.check_type = "ping"
            check2.last_run = djangotime.now()
            check2.email_alert = random.choice([True, False])
            check2.text_alert = random.choice([True, False])

            if site in sites5:
                check2.name = "Synology NAS"
                check2.status = "failing"
                check2.ip = "172.17.14.26"
                check2.more_info = ping_fail_output
            else:
                check2.name = "Google"
                check2.status = "passing"
                check2.ip = "8.8.8.8"
                check2.more_info = ping_success_output

            check2.save()

            for i in range(30):
                check2_history = CheckHistory()
                check2_history.check_id = check2.id
                check2_history.x = djangotime.now() - djangotime.timedelta(
                    minutes=i * 2
                )
                if site in sites5:
                    check2_history.y = 1
                    check2_history.results = ping_fail_output
                else:
                    check2_history.y = 0
                    check2_history.results = ping_success_output
                check2_history.save()

            # cpu load check
            check3 = Check()
            check3.agent = agent
            check3.check_type = "cpuload"
            check3.status = "passing"
            check3.last_run = djangotime.now()
            check3.warning_threshold = 70
            check3.error_threshold = 90
            check3.history = [15, 23, 16, 22, 22, 27, 15, 23, 23, 20, 10, 10, 13, 34]
            check3.email_alert = random.choice([True, False])
            check3.text_alert = random.choice([True, False])
            check3.save()

            for i in range(30):
                check3_history = CheckHistory()
                check3_history.check_id = check3.id
                check3_history.x = djangotime.now() - djangotime.timedelta(
                    minutes=i * 2
                )
                check3_history.y = random.randint(2, 79)
                check3_history.save()

            # memory check
            check4 = Check()
            check4.agent = agent
            check4.check_type = "memory"
            check4.status = "passing"
            check4.warning_threshold = 70
            check4.error_threshold = 85
            check4.history = [34, 34, 35, 36, 34, 34, 34, 34, 34, 34]
            check4.email_alert = random.choice([True, False])
            check4.text_alert = random.choice([True, False])
            check4.save()

            for i in range(30):
                check4_history = CheckHistory()
                check4_history.check_id = check4.id
                check4_history.x = djangotime.now() - djangotime.timedelta(
                    minutes=i * 2
                )
                check4_history.y = random.randint(2, 79)
                check4_history.save()

            # script check storage pool
            check5 = Check()
            check5.agent = agent
            check5.check_type = "script"
            check5.status = "passing"
            check5.last_run = djangotime.now()
            check5.email_alert = random.choice([True, False])
            check5.text_alert = random.choice([True, False])
            check5.timeout = 120
            check5.retcode = 0
            check5.execution_time = "4.0000"
            check5.script = check_pool_health
            check5.save()

            for i in range(30):
                check5_history = CheckHistory()
                check5_history.check_id = check5.id
                check5_history.x = djangotime.now() - djangotime.timedelta(
                    minutes=i * 2
                )
                if i == 10 or i == 18:
                    check5_history.y = 1
                else:
                    check5_history.y = 0
                check5_history.save()

            check6 = Check()
            check6.agent = agent
            check6.check_type = "script"
            check6.status = "passing"
            check6.last_run = djangotime.now()
            check6.email_alert = random.choice([True, False])
            check6.text_alert = random.choice([True, False])
            check6.timeout = 120
            check6.retcode = 0
            check6.execution_time = "4.0000"
            check6.script = check_net_aware
            check6.save()

            for i in range(30):
                check6_history = CheckHistory()
                check6_history.check_id = check6.id
                check6_history.x = djangotime.now() - djangotime.timedelta(
                    minutes=i * 2
                )
                check6_history.y = 0
                check6_history.save()

            nla_task = AutomatedTask()
            nla_task.agent = agent
            actions = [
                {
                    "name": restart_nla.name,
                    "type": "script",
                    "script": restart_nla.pk,
                    "timeout": 90,
                    "script_args": [],
                }
            ]
            nla_task.actions = actions
            nla_task.assigned_check = check6
            nla_task.name = "Restart NLA"
            nla_task.task_type = "checkfailure"
            nla_task.win_task_name = "demotask123"
            nla_task.execution_time = "1.8443"
            nla_task.last_run = djangotime.now()
            nla_task.stdout = "no stdout"
            nla_task.retcode = 0
            nla_task.sync_status = "synced"
            nla_task.save()

            spool_task = AutomatedTask()
            spool_task.agent = agent
            actions = [
                {
                    "name": clear_spool.name,
                    "type": "script",
                    "script": clear_spool.pk,
                    "timeout": 90,
                    "script_args": [],
                }
            ]
            spool_task.actions = actions
            spool_task.name = "Clear the print spooler"
            spool_task.task_type = "daily"
            spool_task.run_time_date = djangotime.now() + djangotime.timedelta(
                minutes=10
            )
            spool_task.expire_date = djangotime.now() + djangotime.timedelta(days=753)
            spool_task.daily_interval = 1
            spool_task.weekly_interval = 1
            spool_task.task_repetition_duration = "2h"
            spool_task.task_repetition_interval = "25m"
            spool_task.random_task_delay = "3m"
            spool_task.win_task_name = "demospool123"
            spool_task.last_run = djangotime.now()
            spool_task.retcode = 0
            spool_task.stdout = spooler_stdout
            spool_task.sync_status = "synced"
            spool_task.save()

            tmp_dir_task = AutomatedTask()
            tmp_dir_task.agent = agent
            tmp_dir_task.name = "show temp dir files"
            actions = [
                {
                    "name": show_tmp_dir_script.name,
                    "type": "script",
                    "script": show_tmp_dir_script.pk,
                    "timeout": 90,
                    "script_args": [],
                }
            ]
            tmp_dir_task.actions = actions
            tmp_dir_task.task_type = "manual"
            tmp_dir_task.win_task_name = "demotemp"
            tmp_dir_task.last_run = djangotime.now()
            tmp_dir_task.stdout = temp_dir_stdout
            tmp_dir_task.retcode = 0
            tmp_dir_task.sync_status = "synced"
            tmp_dir_task.save()

            check7 = Check()
            check7.agent = agent
            check7.check_type = "script"
            check7.status = "passing"
            check7.last_run = djangotime.now()
            check7.email_alert = random.choice([True, False])
            check7.text_alert = random.choice([True, False])
            check7.timeout = 120
            check7.retcode = 0
            check7.execution_time = "3.1337"
            check7.script = clear_spool
            check7.stdout = spooler_stdout
            check7.save()

            for i in range(30):
                check7_history = CheckHistory()
                check7_history.check_id = check7.id
                check7_history.x = djangotime.now() - djangotime.timedelta(
                    minutes=i * 2
                )
                check7_history.y = 0
                check7_history.save()

            check8 = Check()
            check8.agent = agent
            check8.check_type = "winsvc"
            check8.status = "passing"
            check8.last_run = djangotime.now()
            check8.email_alert = random.choice([True, False])
            check8.text_alert = random.choice([True, False])
            check8.more_info = "Status RUNNING"
            check8.fails_b4_alert = 4
            check8.svc_name = "Spooler"
            check8.svc_display_name = "Print Spooler"
            check8.pass_if_start_pending = False
            check8.restart_if_stopped = True
            check8.save()

            for i in range(30):
                check8_history = CheckHistory()
                check8_history.check_id = check8.id
                check8_history.x = djangotime.now() - djangotime.timedelta(
                    minutes=i * 2
                )
                if i == 10 or i == 18:
                    check8_history.y = 1
                    check8_history.results = "Status STOPPED"
                else:
                    check8_history.y = 0
                    check8_history.results = "Status RUNNING"
                check8_history.save()

            check9 = Check()
            check9.agent = agent
            check9.check_type = "eventlog"
            check9.name = "unexpected shutdown"

            check9.last_run = djangotime.now()
            check9.email_alert = random.choice([True, False])
            check9.text_alert = random.choice([True, False])
            check9.fails_b4_alert = 2

            if site in sites5:
                check9.extra_details = eventlog_check_fail_data
                check9.status = "failing"
            else:
                check9.extra_details = {"log": []}
                check9.status = "passing"

            check9.log_name = "Application"
            check9.event_id = 1001
            check9.event_type = "INFO"
            check9.fail_when = "contains"
            check9.search_last_days = 30

            check9.save()

            for i in range(30):
                check9_history = CheckHistory()
                check9_history.check_id = check9.id
                check9_history.x = djangotime.now() - djangotime.timedelta(
                    minutes=i * 2
                )
                if i == 10 or i == 18:
                    check9_history.y = 1
                    check9_history.results = "Events Found: 16"
                else:
                    check9_history.y = 0
                    check9_history.results = "Events Found: 0"
                check9_history.save()

            pick = random.randint(1, 10)

            if pick == 5 or pick == 3:

                reboot_time = djangotime.now() + djangotime.timedelta(
                    minutes=random.randint(1000, 500000)
                )
                date_obj = dt.datetime.strftime(reboot_time, "%Y-%m-%d %H:%M")

                obj = dt.datetime.strptime(date_obj, "%Y-%m-%d %H:%M")

                task_name = "TacticalRMM_SchedReboot_" + "".join(
                    random.choice(string.ascii_letters) for _ in range(10)
                )

                sched_reboot = PendingAction()
                sched_reboot.agent = agent
                sched_reboot.action_type = "schedreboot"
                sched_reboot.details = {
                    "time": str(obj),
                    "taskname": task_name,
                }
                sched_reboot.save()

            self.stdout.write(self.style.SUCCESS(f"Added agent # {count_agents + 1}"))

        call_command("load_demo_scripts")
        self.stdout.write("done")
