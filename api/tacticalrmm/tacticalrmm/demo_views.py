import json
import random

from django.conf import settings
from rest_framework.response import Response

SVC_FILE = settings.BASE_DIR.joinpath("tacticalrmm/test_data/winsvcs.json")
PROCS_FILE = settings.BASE_DIR.joinpath("tacticalrmm/test_data/procs.json")
EVT_LOG_FILE = settings.BASE_DIR.joinpath("tacticalrmm/test_data/appeventlog.json")


def demo_get_services():
    with open(SVC_FILE, "r") as f:
        svcs = json.load(f)

    return Response(svcs)


# simulate realtime process monitor
def demo_get_procs():
    with open(PROCS_FILE, "r") as f:
        procs = json.load(f)

    ret = []
    for proc in procs:
        tmp = {}
        for _, _ in proc.items():
            tmp["name"] = proc["name"]
            tmp["pid"] = proc["pid"]
            tmp["membytes"] = random.randrange(423424, 938921325)
            tmp["username"] = proc["username"]
            tmp["id"] = proc["id"]
            tmp["cpu_percent"] = "{:.2f}".format(random.uniform(0.1, 99.4))
        ret.append(tmp)

    return Response(ret)


def demo_get_eventlog():
    with open(EVT_LOG_FILE, "r") as f:
        logs = json.load(f)

    return Response(logs)
