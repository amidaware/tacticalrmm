from model_bakery.recipe import Recipe

check = Recipe("checks.Check")

diskspace_check = check.extend(
    check_type="diskspace", disk="C:", warning_threshold=30, error_threshold=10
)

cpuload_check = check.extend(
    check_type="cpuload", warning_threshold=30, error_threshold=75
)

ping_check = check.extend(check_type="ping", ip="10.10.10.10")

memory_check = check.extend(
    check_type="memory", warning_threshold=60, error_threshold=75
)

winsvc_check = check.extend(
    check_type="winsvc",
    svc_name="ServiceName",
    svc_display_name="ServiceName",
    svc_policy_mode="manual",
    pass_if_svc_not_exist=False,
)

eventlog_check = check.extend(
    check_type="eventlog", event_id=5000, event_type="application"
)

script_check = check.extend(
    name="Script Name", check_type="script", script__name="Script Name"
)
