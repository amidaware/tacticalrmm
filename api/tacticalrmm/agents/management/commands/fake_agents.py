import datetime as dt
import json
import random
import string

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone as djangotime

from accounts.models import User
from agents.models import Agent, AgentHistory
from automation.models import Policy
from autotasks.models import AutomatedTask, TaskResult
from checks.models import Check, CheckHistory, CheckResult
from clients.models import Client, Site
from logs.models import AuditLog, PendingAction
from scripts.models import Script
from software.models import InstalledSoftware
from tacticalrmm.constants import (
    AgentHistoryType,
    AgentMonType,
    AgentPlat,
    AlertSeverity,
    CheckStatus,
    CheckType,
    EvtLogFailWhen,
    EvtLogNames,
    EvtLogTypes,
    GoArch,
    PAAction,
    ScriptShell,
    TaskSyncStatus,
    TaskType,
)
from tacticalrmm.demo_data import (
    check_network_loc_aware_ps1,
    check_storage_pool_health_ps1,
    clear_print_spool_bat,
    disks,
    disks_linux_deb,
    disks_linux_pi,
    ping_fail_output,
    ping_success_output,
    restart_nla_ps1,
    show_temp_dir_py,
    spooler_stdout,
    temp_dir_stdout,
    wmi_deb,
    wmi_pi,
    wmi_mac,
    disks_mac,
)
from winupdate.models import WinUpdate, WinUpdatePolicy

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

    def rand_string(self, length: int) -> str:
        chars = string.ascii_letters
        return "".join(random.choice(chars) for _ in range(length))

    def handle(self, *args, **kwargs) -> None:
        user = User.objects.first()
        if user:
            user.totp_key = "ABSA234234"
            user.save(update_fields=["totp_key"])

        Agent.objects.all().delete()
        Client.objects.all().delete()
        Check.objects.all().delete()
        Script.objects.all().delete()
        AutomatedTask.objects.all().delete()
        CheckHistory.objects.all().delete()
        Policy.objects.all().delete()
        AuditLog.objects.all().delete()
        PendingAction.objects.all().delete()

        call_command("load_community_scripts")
        call_command("initial_db_setup")
        call_command("load_chocos")
        call_command("create_installer_user")

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

        clients = (
            "Company 1",
            "Company 2",
            "Company 3",
            "Company 4",
            "Company 5",
            "Company 6",
        )
        sites1 = ("HQ1", "LA Office 1", "NY Office 1")
        sites2 = ("HQ2", "LA Office 2", "NY Office 2")
        sites3 = ("HQ3", "LA Office 3", "NY Office 3")
        sites4 = ("HQ4", "LA Office 4", "NY Office 4")
        sites5 = ("HQ5", "LA Office 5", "NY Office 5")
        sites6 = ("HQ6", "LA Office 6", "NY Office 6")

        client1 = Client(name=clients[0])
        client2 = Client(name=clients[1])
        client3 = Client(name=clients[2])
        client4 = Client(name=clients[3])
        client5 = Client(name=clients[4])
        client6 = Client(name=clients[5])

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

        hostnames = (
            "DC-1",
            "DC-2",
            "FSV-1",
            "FSV-2",
            "WSUS",
            "DESKTOP-12345",
            "LAPTOP-55443",
            "db-aws-01",
            "Karens-MacBook-Air.local",
        )
        descriptions = ("Bob's computer", "Primary DC", "File Server", "Karen's Laptop")
        modes = AgentMonType.values
        op_systems_servers = (
            "Microsoft Windows Server 2016 Standard, 64bit (build 14393)",
            "Microsoft Windows Server 2012 R2 Standard, 64bit (build 9600)",
            "Microsoft Windows Server 2019 Standard, 64bit (build 17763)",
        )

        op_systems_workstations = (
            "Microsoft Windows 8.1 Pro, 64bit (build 9600)",
            "Microsoft Windows 10 Pro for Workstations, 64bit (build 18363)",
            "Microsoft Windows 10 Pro, 64bit (build 18363)",
        )

        linux_deb_os = "Debian 11.2 x86_64 5.10.0-11-amd64"
        linux_pi_os = "Raspbian 11.2 armv7l 5.10.92-v7+"
        mac_os = "Darwin 12.5.1 arm64 21.6.0"

        public_ips = ("65.234.22.4", "74.123.43.5", "44.21.134.45")

        total_rams = (4, 8, 16, 32, 64, 128)

        now = dt.datetime.now()
        django_now = djangotime.now()

        boot_times = []

        for _ in range(15):
            rand_hour = now - dt.timedelta(hours=random.randint(1, 22))
            boot_times.append(str(rand_hour.timestamp()))

        for _ in range(5):
            rand_days = now - dt.timedelta(days=random.randint(2, 50))
            boot_times.append(str(rand_days.timestamp()))

        user_names = ("None", "Karen", "Steve", "jsmith", "jdoe")

        with open(SVCS) as f:
            services = json.load(f)

        # WMI
        with open(WMI_1) as f:
            wmi1 = json.load(f)

        with open(WMI_2) as f:
            wmi2 = json.load(f)

        with open(WMI_3) as f:
            wmi3 = json.load(f)

        wmi_details = [i for i in (wmi1, wmi2, wmi3)]

        # software
        with open(SW_1) as f:
            software1 = json.load(f)

        with open(SW_2) as f:
            software2 = json.load(f)

        softwares = [i for i in (software1, software2)]

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
        clear_spool.shell = ScriptShell.CMD
        clear_spool.script_body = clear_print_spool_bat
        clear_spool.save()

        check_net_aware = Script()
        check_net_aware.name = "Check Network Location Awareness"
        check_net_aware.description = "Check's network location awareness on domain computers, should always be domain profile and not public or private. Sometimes happens when computer restarts before domain available. This script will return 0 if check passes or 1 if it fails."
        check_net_aware.filename = "check_network_loc_aware.ps1"
        check_net_aware.shell = ScriptShell.POWERSHELL
        check_net_aware.script_body = check_network_loc_aware_ps1
        check_net_aware.save()

        check_pool_health = Script()
        check_pool_health.name = "Check storage spool health"
        check_pool_health.description = "loops through all storage pools and will fail if any of them are not healthy"
        check_pool_health.filename = "check_storage_pool_health.ps1"
        check_pool_health.shell = ScriptShell.POWERSHELL
        check_pool_health.script_body = check_storage_pool_health_ps1
        check_pool_health.save()

        restart_nla = Script()
        restart_nla.name = "Restart NLA Service"
        restart_nla.description = "restarts the Network Location Awareness windows service to fix the nic profile. Run this after the check network service fails"
        restart_nla.filename = "restart_nla.ps1"
        restart_nla.shell = ScriptShell.POWERSHELL
        restart_nla.script_body = restart_nla_ps1
        restart_nla.save()

        show_tmp_dir_script = Script()
        show_tmp_dir_script.name = "Check temp dir"
        show_tmp_dir_script.description = "shows files in temp dir using python"
        show_tmp_dir_script.filename = "show_temp_dir.py"
        show_tmp_dir_script.shell = ScriptShell.PYTHON
        show_tmp_dir_script.script_body = show_temp_dir_py
        show_tmp_dir_script.save()

        for count_agents in range(AGENTS_TO_GENERATE):
            client = random.choice(clients)

            if client == clients[0]:
                site = random.choice(sites1)
            elif client == clients[1]:
                site = random.choice(sites2)
            elif client == clients[2]:
                site = random.choice(sites3)
            elif client == clients[3]:
                site = random.choice(sites4)
            elif client == clients[4]:
                site = random.choice(sites5)
            elif client == clients[5]:
                site = random.choice(sites6)

            agent = Agent()

            plat_pick = random.randint(1, 15)
            if plat_pick in (7, 11):
                agent.plat = AgentPlat.LINUX
                mode = AgentMonType.SERVER
                # pi arm
                if plat_pick == 7:
                    agent.goarch = GoArch.ARM32
                    agent.wmi_detail = wmi_pi
                    agent.disks = disks_linux_pi
                    agent.operating_system = linux_pi_os
                else:
                    agent.goarch = GoArch.AMD64
                    agent.wmi_detail = wmi_deb
                    agent.disks = disks_linux_deb
                    agent.operating_system = linux_deb_os
            elif plat_pick in (4, 14):
                agent.plat = AgentPlat.DARWIN
                mode = random.choice([AgentMonType.SERVER, AgentMonType.WORKSTATION])
                agent.goarch = GoArch.ARM64
                agent.wmi_detail = wmi_mac
                agent.disks = disks_mac
                agent.operating_system = mac_os
            else:
                agent.plat = AgentPlat.WINDOWS
                agent.goarch = GoArch.AMD64
                mode = random.choice(modes)
                agent.wmi_detail = random.choice(wmi_details)
                agent.services = services
                agent.disks = random.choice(disks)
                if mode == AgentMonType.SERVER:
                    agent.operating_system = random.choice(op_systems_servers)
                else:
                    agent.operating_system = random.choice(op_systems_workstations)

            agent.version = settings.LATEST_AGENT_VER
            agent.hostname = random.choice(hostnames)
            agent.site = Site.objects.get(name=site)
            agent.agent_id = self.rand_string(40)
            agent.description = random.choice(descriptions)
            agent.monitoring_type = mode
            agent.public_ip = random.choice(public_ips)
            agent.last_seen = django_now

            agent.total_ram = random.choice(total_rams)
            agent.boot_time = random.choice(boot_times)
            agent.logged_in_username = random.choice(user_names)
            agent.mesh_node_id = (
                "3UiLhe420@kaVQ0rswzBeonW$WY0xrFFUDBQlcYdXoriLXzvPmBpMrV99vRHXFlb"
            )
            agent.overdue_email_alert = random.choice([True, False])
            agent.overdue_text_alert = random.choice([True, False])
            agent.needs_reboot = random.choice([True, False])

            agent.save()

            if agent.plat == AgentPlat.WINDOWS:
                InstalledSoftware(agent=agent, software=random.choice(softwares)).save()

            if mode == AgentMonType.WORKSTATION:
                WinUpdatePolicy(agent=agent, run_time_days=[5, 6]).save()
            else:
                WinUpdatePolicy(agent=agent).save()

            if agent.plat == AgentPlat.WINDOWS:
                # windows updates load
                guids = [i for i in windows_updates.keys()]
                for i in guids:
                    WinUpdate(
                        agent=agent,
                        guid=i,
                        kb=windows_updates[i]["KBs"][0],
                        title=windows_updates[i]["Title"],
                        installed=windows_updates[i]["Installed"],
                        downloaded=windows_updates[i]["Downloaded"],
                        description=windows_updates[i]["Description"],
                        severity=windows_updates[i]["Severity"],
                    ).save()

            # agent histories
            hist = AgentHistory()
            hist.agent = agent
            hist.type = AgentHistoryType.CMD_RUN
            hist.command = "ping google.com"
            hist.username = "demo"
            hist.results = ping_success_output
            hist.save()

            hist1 = AgentHistory()
            hist1.agent = agent
            hist1.type = AgentHistoryType.SCRIPT_RUN
            hist1.script = clear_spool
            hist1.script_results = {
                "id": 1,
                "stderr": "",
                "stdout": spooler_stdout,
                "execution_time": 3.5554593,
                "retcode": 0,
            }
            hist1.save()

            if agent.plat == AgentPlat.WINDOWS:
                # disk space check
                check1 = Check()
                check1.agent = agent
                check1.check_type = CheckType.DISK_SPACE
                check1.warning_threshold = 25
                check1.error_threshold = 10
                check1.disk = "C:"
                check1.email_alert = random.choice([True, False])
                check1.text_alert = random.choice([True, False])
                check1.save()

                check_result1 = CheckResult()
                check_result1.agent = agent
                check_result1.assigned_check = check1
                check_result1.status = CheckStatus.PASSING
                check_result1.last_run = django_now
                check_result1.more_info = "Total: 498.7GB, Free: 287.4GB"
                check_result1.save()

                for i in range(30):
                    check1_history = CheckHistory()
                    check1_history.check_id = check1.pk
                    check1_history.agent_id = agent.agent_id
                    check1_history.x = django_now - djangotime.timedelta(minutes=i * 2)
                    check1_history.y = random.randint(13, 40)
                    check1_history.save()

            # ping check
            check2 = Check()
            check_result2 = CheckResult()

            check2.agent = agent
            check2.check_type = CheckType.PING

            check2.email_alert = random.choice([True, False])
            check2.text_alert = random.choice([True, False])

            check_result2.agent = agent
            check_result2.assigned_check = check2
            check_result2.last_run = django_now

            if site in sites5:
                check2.name = "Synology NAS"
                check2.alert_severity = AlertSeverity.ERROR
                check_result2.status = CheckStatus.FAILING
                check2.ip = "172.17.14.26"
                check_result2.more_info = ping_fail_output
            else:
                check2.name = "Google"
                check_result2.status = CheckStatus.PASSING
                check2.ip = "8.8.8.8"
                check_result2.more_info = ping_success_output

            check2.save()
            check_result2.save()

            for i in range(30):
                check2_history = CheckHistory()
                check2_history.check_id = check2.pk
                check2_history.agent_id = agent.agent_id
                check2_history.x = django_now - djangotime.timedelta(minutes=i * 2)
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
            check3.check_type = CheckType.CPU_LOAD
            check3.warning_threshold = 70
            check3.error_threshold = 90
            check3.email_alert = random.choice([True, False])
            check3.text_alert = random.choice([True, False])
            check3.save()

            check_result3 = CheckResult()
            check_result3.agent = agent
            check_result3.assigned_check = check3
            check_result3.status = CheckStatus.PASSING
            check_result3.last_run = django_now
            check_result3.history = [
                15,
                23,
                16,
                22,
                22,
                27,
                15,
                23,
                23,
                20,
                10,
                10,
                13,
                34,
            ]
            check_result3.save()

            for i in range(30):
                check3_history = CheckHistory()
                check3_history.check_id = check3.pk
                check3_history.agent_id = agent.agent_id
                check3_history.x = django_now - djangotime.timedelta(minutes=i * 2)
                check3_history.y = random.randint(2, 79)
                check3_history.save()

            # memory check
            check4 = Check()
            check4.agent = agent
            check4.check_type = CheckType.MEMORY
            check4.warning_threshold = 70
            check4.error_threshold = 85
            check4.email_alert = random.choice([True, False])
            check4.text_alert = random.choice([True, False])
            check4.save()

            check_result4 = CheckResult()
            check_result4.agent = agent
            check_result4.assigned_check = check4
            check_result4.status = CheckStatus.PASSING
            check_result4.last_run = django_now
            check_result4.history = [34, 34, 35, 36, 34, 34, 34, 34, 34, 34]
            check_result4.save()

            for i in range(30):
                check4_history = CheckHistory()
                check4_history.check_id = check4.pk
                check4_history.agent_id = agent.agent_id
                check4_history.x = django_now - djangotime.timedelta(minutes=i * 2)
                check4_history.y = random.randint(2, 79)
                check4_history.save()

            # script check storage pool
            check5 = Check()

            check5.agent = agent
            check5.check_type = CheckType.SCRIPT

            check5.email_alert = random.choice([True, False])
            check5.text_alert = random.choice([True, False])
            check5.timeout = 120

            check5.script = check_pool_health
            check5.save()

            check_result5 = CheckResult()
            check_result5.agent = agent
            check_result5.assigned_check = check5
            check_result5.status = CheckStatus.PASSING
            check_result5.last_run = django_now
            check_result5.retcode = 0
            check_result5.execution_time = "4.0000"
            check_result5.save()

            for i in range(30):
                check5_history = CheckHistory()
                check5_history.check_id = check5.pk
                check5_history.agent_id = agent.agent_id
                check5_history.x = django_now - djangotime.timedelta(minutes=i * 2)
                if i == 10 or i == 18:
                    check5_history.y = 1
                else:
                    check5_history.y = 0
                check5_history.results = {
                    "retcode": 0,
                    "stdout": None,
                    "stderr": None,
                    "execution_time": "4.0000",
                }
                check5_history.save()

            check6 = Check()

            check6.agent = agent
            check6.check_type = CheckType.SCRIPT
            check6.email_alert = random.choice([True, False])
            check6.text_alert = random.choice([True, False])
            check6.timeout = 120
            check6.script = check_net_aware
            check6.save()

            check_result6 = CheckResult()
            check_result6.agent = agent
            check_result6.assigned_check = check6
            check_result6.status = CheckStatus.PASSING
            check_result6.last_run = django_now
            check_result6.retcode = 0
            check_result6.execution_time = "4.0000"
            check_result6.save()

            for i in range(30):
                check6_history = CheckHistory()
                check6_history.check_id = check6.pk
                check6_history.agent_id = agent.agent_id
                check6_history.x = django_now - djangotime.timedelta(minutes=i * 2)
                check6_history.y = 0
                check6_history.results = {
                    "retcode": 0,
                    "stdout": None,
                    "stderr": None,
                    "execution_time": "4.0000",
                }
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
            nla_task.task_type = TaskType.CHECK_FAILURE
            nla_task.save()

            nla_task_result = TaskResult()
            nla_task_result.task = nla_task
            nla_task_result.agent = agent
            nla_task_result.execution_time = "1.8443"
            nla_task_result.last_run = django_now
            nla_task_result.stdout = "no stdout"
            nla_task_result.retcode = 0
            nla_task_result.sync_status = TaskSyncStatus.SYNCED
            nla_task_result.save()

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
            spool_task.task_type = TaskType.DAILY
            spool_task.run_time_date = django_now + djangotime.timedelta(minutes=10)
            spool_task.expire_date = django_now + djangotime.timedelta(days=753)
            spool_task.daily_interval = 1
            spool_task.weekly_interval = 1
            spool_task.task_repetition_duration = "2h"
            spool_task.task_repetition_interval = "25m"
            spool_task.random_task_delay = "3m"
            spool_task.save()

            spool_task_result = TaskResult()
            spool_task_result.task = spool_task
            spool_task_result.agent = agent
            spool_task_result.last_run = django_now
            spool_task_result.retcode = 0
            spool_task_result.stdout = spooler_stdout
            spool_task_result.sync_status = TaskSyncStatus.SYNCED
            spool_task_result.save()

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
            tmp_dir_task.task_type = TaskType.MANUAL
            tmp_dir_task.save()

            tmp_dir_task_result = TaskResult()
            tmp_dir_task_result.task = tmp_dir_task
            tmp_dir_task_result.agent = agent
            tmp_dir_task_result.last_run = django_now
            tmp_dir_task_result.stdout = temp_dir_stdout
            tmp_dir_task_result.retcode = 0
            tmp_dir_task_result.sync_status = TaskSyncStatus.SYNCED
            tmp_dir_task_result.save()

            check7 = Check()

            check7.agent = agent
            check7.check_type = CheckType.SCRIPT

            check7.email_alert = random.choice([True, False])
            check7.text_alert = random.choice([True, False])
            check7.timeout = 120

            check7.script = clear_spool

            check7.save()

            check_result7 = CheckResult()
            check_result7.assigned_check = check7
            check_result7.agent = agent
            check_result7.status = CheckStatus.PASSING
            check_result7.last_run = django_now
            check_result7.retcode = 0
            check_result7.execution_time = "3.1337"
            check_result7.stdout = spooler_stdout
            check_result7.save()

            for i in range(30):
                check7_history = CheckHistory()
                check7_history.check_id = check7.pk
                check7_history.agent_id = agent.agent_id
                check7_history.x = django_now - djangotime.timedelta(minutes=i * 2)
                check7_history.y = 0
                check7_history.results = {
                    "retcode": 0,
                    "stdout": spooler_stdout,
                    "stderr": None,
                    "execution_time": "3.1337",
                }
                check7_history.save()

            if agent.plat == AgentPlat.WINDOWS:
                check8 = Check()
                check8.agent = agent
                check8.check_type = CheckType.WINSVC
                check8.email_alert = random.choice([True, False])
                check8.text_alert = random.choice([True, False])
                check8.fails_b4_alert = 4
                check8.svc_name = "Spooler"
                check8.svc_display_name = "Print Spooler"
                check8.pass_if_start_pending = False
                check8.restart_if_stopped = True
                check8.save()

                check_result8 = CheckResult()
                check_result8.assigned_check = check8
                check_result8.agent = agent
                check_result8.status = CheckStatus.PASSING
                check_result8.last_run = django_now
                check_result8.more_info = "Status RUNNING"
                check_result8.save()

                for i in range(30):
                    check8_history = CheckHistory()
                    check8_history.check_id = check8.pk
                    check8_history.agent_id = agent.agent_id
                    check8_history.x = django_now - djangotime.timedelta(minutes=i * 2)
                    if i == 10 or i == 18:
                        check8_history.y = 1
                        check8_history.results = "Status STOPPED"
                    else:
                        check8_history.y = 0
                        check8_history.results = "Status RUNNING"
                    check8_history.save()

                check9 = Check()
                check9.agent = agent
                check9.check_type = CheckType.EVENT_LOG
                check9.name = "unexpected shutdown"
                check9.email_alert = random.choice([True, False])
                check9.text_alert = random.choice([True, False])
                check9.fails_b4_alert = 2
                check9.log_name = EvtLogNames.APPLICATION
                check9.event_id = 1001
                check9.event_type = EvtLogTypes.INFO
                check9.fail_when = EvtLogFailWhen.CONTAINS
                check9.search_last_days = 30

                check_result9 = CheckResult()
                check_result9.agent = agent
                check_result9.assigned_check = check9

                check_result9.last_run = django_now
                if site in sites5:
                    check_result9.extra_details = eventlog_check_fail_data
                    check_result9.status = CheckStatus.FAILING
                else:
                    check_result9.extra_details = {"log": []}
                    check_result9.status = CheckStatus.PASSING

                check9.save()
                check_result9.save()

                for i in range(30):
                    check9_history = CheckHistory()
                    check9_history.check_id = check9.pk
                    check9_history.agent_id = agent.agent_id
                    check9_history.x = django_now - djangotime.timedelta(minutes=i * 2)
                    if i == 10 or i == 18:
                        check9_history.y = 1
                        check9_history.results = "Events Found: 16"
                    else:
                        check9_history.y = 0
                        check9_history.results = "Events Found: 0"
                    check9_history.save()

                pick = random.randint(1, 10)

                if pick == 5 or pick == 3:
                    reboot_time = django_now + djangotime.timedelta(
                        minutes=random.randint(1000, 500000)
                    )
                    date_obj = dt.datetime.strftime(reboot_time, "%Y-%m-%d %H:%M")

                    obj = dt.datetime.strptime(date_obj, "%Y-%m-%d %H:%M")

                    task_name = "TacticalRMM_SchedReboot_" + "".join(
                        random.choice(string.ascii_letters) for _ in range(10)
                    )

                    sched_reboot = PendingAction()
                    sched_reboot.agent = agent
                    sched_reboot.action_type = PAAction.SCHED_REBOOT
                    sched_reboot.details = {
                        "time": str(obj),
                        "taskname": task_name,
                    }
                    sched_reboot.save()

            self.stdout.write(self.style.SUCCESS(f"Added agent # {count_agents + 1}"))

        self.stdout.write("done")
