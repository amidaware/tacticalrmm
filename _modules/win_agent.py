from __future__ import absolute_import
import psutil
import os
import datetime
import zlib
import json
import base64
import wmi
import win32evtlog
import win32con
import win32evtlogutil
import winerror
from time import sleep
import requests
import subprocess

PROGRAM_DIR = "C:\\Program Files\\TacticalAgent"
TAC_RMM = os.path.join(PROGRAM_DIR, "tacticalrmm.exe")
NSSM = os.path.join(PROGRAM_DIR, "nssm.exe")
SALT_CALL = os.path.join("C:\\salt", "salt-call.bat")
TEMP_DIR = os.path.join("C:\\Windows", "Temp")


def get_services():
    return [svc.as_dict() for svc in psutil.win_service_iter()]


def run_python_script(filename, timeout):
    python_bin = os.path.join("c:\\salt\\bin", "python.exe")
    file_path = os.path.join("c:\\windows\\temp", filename)
    __salt__["cp.get_file"](
        "salt://scripts/userdefined/{0}".format(filename), file_path
    )
    return __salt__["cmd.run_all"](
        "{0} {1}".format(python_bin, file_path), timeout=timeout
    )


def uninstall_agent():
    remove_exe = os.path.join(PROGRAM_DIR, "unins000.exe")
    __salt__["cmd.run_bg"]([remove_exe, "/VERYSILENT", "/SUPPRESSMSGBOXES"])
    return "ok"


def update_salt():
    __salt__["cmd.run_bg"]([TAC_RMM, "-m", "updatesalt"])
    return "ok"


def run_manual_checks():
    __salt__["cmd.run_bg"]([TAC_RMM, "-m", "runchecks"])
    return "ok"


def install_updates():
    return __salt__["cmd.run_bg"]([TAC_RMM, "-m", "winupdater"])


def agent_update(version, url):
    try:
        r = requests.get(url, stream=True, timeout=300)
    except Exception:
        return "failed"

    if r.status_code != 200:
        return "failed"

    exe = os.path.join(TEMP_DIR, f"winagent-v{version}.exe")

    with open(exe, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    del r

    services = ("tacticalagent", "checkrunner")

    for svc in services:
        subprocess.run([NSSM, "stop", svc], timeout=120)

    sleep(5)
    r = subprocess.run([exe, "/VERYSILENT", "/SUPPRESSMSGBOXES"], timeout=300)
    sleep(10)

    for svc in services:
        subprocess.run([NSSM, "start", svc], timeout=120)

    return "ok"


def do_agent_update(version, url):
    return __salt__["cmd.run_bg"](
        [
            "C:\\salt\\salt-call.bat",
            "win_agent.agent_update",
            f"version={version}",
            f"url={url}",
            "--local",
        ]
    )


class SystemDetail:
    def __init__(self):
        self.c = wmi.WMI()
        self.comp_sys_prod = self.c.Win32_ComputerSystemProduct()
        self.comp_sys = self.c.Win32_ComputerSystem()
        self.memory = self.c.Win32_PhysicalMemory()
        self.os = self.c.Win32_OperatingSystem()
        self.base_board = self.c.Win32_BaseBoard()
        self.bios = self.c.Win32_BIOS()
        self.disk = self.c.Win32_DiskDrive()
        self.network_adapter = self.c.Win32_NetworkAdapter()
        self.network_config = self.c.Win32_NetworkAdapterConfiguration()
        self.desktop_monitor = self.c.Win32_DesktopMonitor()
        self.cpu = self.c.Win32_Processor()
        self.usb = self.c.Win32_USBController()

    def get_all(self, obj):
        ret = []
        for i in obj:
            tmp = [
                {j: getattr(i, j)}
                for j in list(i.properties)
                if getattr(i, j) is not None
            ]
            ret.append(tmp)

        return ret


def system_info():
    info = SystemDetail()
    return {
        "comp_sys_prod": info.get_all(info.comp_sys_prod),
        "comp_sys": info.get_all(info.comp_sys),
        "mem": info.get_all(info.memory),
        "os": info.get_all(info.os),
        "base_board": info.get_all(info.base_board),
        "bios": info.get_all(info.bios),
        "disk": info.get_all(info.disk),
        "network_adapter": info.get_all(info.network_adapter),
        "network_config": info.get_all(info.network_config),
        "desktop_monitor": info.get_all(info.desktop_monitor),
        "cpu": info.get_all(info.cpu),
        "usb": info.get_all(info.usb),
    }


def get_procs():
    ret = []

    # setup
    for proc in psutil.process_iter():
        with proc.oneshot():
            proc.cpu_percent(interval=None)

    # need time for psutil to record cpu percent
    sleep(1)

    for c, proc in enumerate(psutil.process_iter(), 1):
        x = {}
        with proc.oneshot():
            if proc.pid == 0 or not proc.name():
                continue

            x["name"] = proc.name()
            x["cpu_percent"] = proc.cpu_percent(interval=None) / psutil.cpu_count()
            x["memory_percent"] = proc.memory_percent()
            x["pid"] = proc.pid
            x["ppid"] = proc.ppid()
            x["status"] = proc.status()
            x["username"] = proc.username()
            x["id"] = c

        ret.append(x)

    return ret


def _compress_json(j):
    return {
        "wineventlog": base64.b64encode(
            zlib.compress(json.dumps(j).encode("utf-8", errors="ignore"))
        ).decode("ascii", errors="ignore")
    }


def get_eventlog(logtype, last_n_days):

    start_time = datetime.datetime.now() - datetime.timedelta(days=last_n_days)
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

    status_dict = {
        win32con.EVENTLOG_AUDIT_FAILURE: "AUDIT_FAILURE",
        win32con.EVENTLOG_AUDIT_SUCCESS: "AUDIT_SUCCESS",
        win32con.EVENTLOG_INFORMATION_TYPE: "INFO",
        win32con.EVENTLOG_WARNING_TYPE: "WARNING",
        win32con.EVENTLOG_ERROR_TYPE: "ERROR",
        0: "INFO",
    }

    computer = "localhost"
    hand = win32evtlog.OpenEventLog(computer, logtype)
    total = win32evtlog.GetNumberOfEventLogRecords(hand)
    log = []
    uid = 0
    done = False

    try:
        while 1:
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            for ev_obj in events:

                uid += 1
                # return once total number of events reach or we'll be stuck in an infinite loop
                if uid >= total:
                    done = True
                    break

                the_time = ev_obj.TimeGenerated.Format()
                time_obj = datetime.datetime.strptime(the_time, "%c")
                if time_obj < start_time:
                    done = True
                    break

                computer = str(ev_obj.ComputerName)
                src = str(ev_obj.SourceName)
                evt_type = str(status_dict[ev_obj.EventType])
                evt_id = str(winerror.HRESULT_CODE(ev_obj.EventID))
                evt_category = str(ev_obj.EventCategory)
                record = str(ev_obj.RecordNumber)
                msg = (
                    str(win32evtlogutil.SafeFormatMessage(ev_obj, logtype))
                    .replace("<", "")
                    .replace(">", "")
                )

                event_dict = {
                    "computer": computer,
                    "source": src,
                    "eventType": evt_type,
                    "eventID": evt_id,
                    "eventCategory": evt_category,
                    "message": msg,
                    "time": the_time,
                    "record": record,
                    "uid": uid,
                }

                log.append(event_dict)

            if done:
                break

    except Exception:
        pass

    win32evtlog.CloseEventLog(hand)
    return _compress_json(log)
