from model_bakery.recipe import Recipe

from tacticalrmm.constants import CheckType, EvtLogTypes

check = Recipe("checks.Check")

diskspace_check = check.extend(
    check_type=CheckType.DISK_SPACE, disk="C:", warning_threshold=30, error_threshold=10
)

cpuload_check = check.extend(
    check_type=CheckType.CPU_LOAD, warning_threshold=30, error_threshold=75
)

ping_check = check.extend(check_type="ping", ip="10.10.10.10")

memory_check = check.extend(
    check_type=CheckType.MEMORY, warning_threshold=60, error_threshold=75
)

winsvc_check = check.extend(
    check_type=CheckType.WINSVC,
    svc_name="ServiceName",
    svc_display_name="ServiceName",
    svc_policy_mode="manual",
    pass_if_svc_not_exist=False,
)

eventlog_check = check.extend(
    check_type=CheckType.EVENT_LOG, event_id=5000, event_type=EvtLogTypes.INFO
)

script_check = check.extend(
    name="Script Name", check_type=CheckType.SCRIPT, script__name="Script Name"
)
