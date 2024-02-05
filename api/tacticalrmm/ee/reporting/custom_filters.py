from contextlib import suppress
from zoneinfo import ZoneInfo

import validators


def as_tz(date_obj, tz, format="%b %d %Y, %I:%M %p"):
    return date_obj.astimezone(ZoneInfo(tz)).strftime(format)


def local_ips(wmi_detail):
    ret = []
    with suppress(Exception):
        ips = wmi_detail["network_config"]
        for i in ips:
            try:
                addr = [x["IPAddress"] for x in i if "IPAddress" in x][0]
            except:
                continue

            if addr is None:
                continue

            for ip in addr:
                if validators.ipv4(ip):
                    ret.append(ip)

    return ret
