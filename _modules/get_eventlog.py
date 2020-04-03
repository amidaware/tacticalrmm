from __future__ import absolute_import
import win32evtlog
import win32con
import win32evtlogutil
import winerror
import datetime
import zlib
import json
import base64


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
    log = []
    uid = 0

    try:
        uid = 0
        while 1:
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            for ev_obj in events:

                the_time = ev_obj.TimeGenerated.Format()
                time_obj = datetime.datetime.strptime(the_time, "%c")
                if time_obj < start_time:
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
                uid += 1

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

            if time_obj < start_time:
                break

    except Exception:
        pass

    win32evtlog.CloseEventLog(hand)
    return _compress_json(log)
