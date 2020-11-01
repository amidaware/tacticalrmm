from .models import Check
from model_bakery.recipe import Recipe, seq

check = Recipe(Check)

diskspace_check = check.extend(check_type="diskspace", disk="C:", threshold=75)

cpuload_check = check.extend(check_type="cpuload", threshold=75)

ping_check = check.extend(check_type="ping", ip="10.10.10.10")

memory_check = check.extend(check_type="memory", threshold=75)

winsvc_check = check.extend(
    check_type="winsvc",
    svc_name="ServiceName",
    svc_display_name="ServiceName",
    svc_policy_mode="manual",
)

eventlog_check = check.extend(
    check_type="eventlog", event_id=5000, event_type="application"
)

script_check = check.extend(
    name="Script Name", check_type="script", script__name="Script Name"
)
