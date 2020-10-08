from .models import Check
from model_bakery.recipe import Recipe, seq
from model_bakery import baker
from itertools import cycle

check = Recipe(
    Check
)

diskspace_check = check.extend(
    check_type="diskspace",
    disk="C:"
)

cpuload_check = check.extend(
    check_type="cpuload",
    threshold="75"
)

ping_check = check.extend(
    check_type="ping",
    ip="10.10.10.10"
)

memory_check = check.extend(
    check_type="memory",
    threshold="75"
)

winsvc_check = check.extend(
    check_type="winsvc",
    svc_name=seq("ServiceName"),
    svc_display_name=seq("ServiceName"),
    svc_policy_mode="manual"
)

eventlog_check = check.extend(
    check_type="eventlog",
    event_id=seq(0),
    event_type="application"
)

script_check = check.extend(
    name="Script Name",
    check_type="script",
    script__name="Script Name"
)
