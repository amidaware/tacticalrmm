import zoneinfo
from enum import Enum

from django.conf import settings
from django.db import models


class MeshAgentIdent(Enum):
    WIN32 = 3
    WIN64 = 4
    LINUX32 = 5
    LINUX64 = 6
    LINUX_ARM_64 = 26
    LINUX_ARM_HF = 25
    DARWIN_UNIVERSAL = 10005

    def __str__(self):
        return str(self.value)


CORESETTINGS_CACHE_KEY = "core_settings"
ROLE_CACHE_PREFIX = "role_"
AGENT_TBL_PEND_ACTION_CNT_CACHE_PREFIX = "agent_tbl_pendingactions_"

AGENT_STATUS_ONLINE = "online"
AGENT_STATUS_OFFLINE = "offline"
AGENT_STATUS_OVERDUE = "overdue"

REDIS_LOCK_EXPIRE = 60 * 60 * 2  # Lock expires in 2 hours
RESOLVE_ALERTS_LOCK = "resolve-alerts-lock-key"
SYNC_SCHED_TASK_LOCK = "sync-sched-tasks-lock-key"
AGENT_OUTAGES_LOCK = "agent-outages-task-lock-key"
ORPHANED_WIN_TASK_LOCK = "orphaned-win-task-lock-key"
SYNC_MESH_PERMS_TASK_LOCK = "sync-mesh-perms-lock-key"

TRMM_WS_MAX_SIZE = getattr(settings, "TRMM_WS_MAX_SIZE", 100 * 2**20)
TRMM_MAX_REQUEST_SIZE = getattr(settings, "TRMM_MAX_REQUEST_SIZE", 10 * 2**20)


class GoArch(models.TextChoices):
    AMD64 = "amd64", "amd64"
    i386 = "386", "386"
    ARM64 = "arm64", "arm64"
    ARM32 = "arm", "arm"


class CustomFieldModel(models.TextChoices):
    CLIENT = "client", "Client"
    SITE = "site", "Site"
    AGENT = "agent", "Agent"


class CustomFieldType(models.TextChoices):
    TEXT = "text", "Text"
    NUMBER = "number", "Number"
    SINGLE = "single", "Single"
    MULTIPLE = "multiple", "Multiple"
    CHECKBOX = "checkbox", "Checkbox"
    DATETIME = "datetime", "DateTime"


class TaskSyncStatus(models.TextChoices):
    SYNCED = "synced", "Synced With Agent"
    NOT_SYNCED = "notsynced", "Waiting On Agent Checkin"
    PENDING_DELETION = "pendingdeletion", "Pending Deletion on Agent"
    INITIAL = "initial", "Initial Task Sync"


class TaskStatus(models.TextChoices):
    PASSING = "passing", "Passing"
    FAILING = "failing", "Failing"
    PENDING = "pending", "Pending"


class TaskType(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    MONTHLY_DOW = "monthlydow", "Monthly Day of Week"
    CHECK_FAILURE = "checkfailure", "On Check Failure"
    MANUAL = "manual", "Manual"
    RUN_ONCE = "runonce", "Run Once"
    ONBOARDING = "onboarding", "Onboarding"
    SCHEDULED = "scheduled", "Scheduled"  # deprecated


class AlertSeverity(models.TextChoices):
    INFO = "info", "Informational"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"


class AlertType(models.TextChoices):
    AVAILABILITY = "availability", "Availability"
    CHECK = "check", "Check"
    TASK = "task", "Task"
    CUSTOM = "custom", "Custom"


class AlertTemplateActionType(models.TextChoices):
    SCRIPT = "script", "Script"
    SERVER = "server", "Server"
    REST = "rest", "Rest"


class AgentHistoryType(models.TextChoices):
    TASK_RUN = "task_run", "Task Run"
    SCRIPT_RUN = "script_run", "Script Run"
    CMD_RUN = "cmd_run", "CMD Run"


class AgentMonType(models.TextChoices):
    SERVER = "server", "Server"
    WORKSTATION = "workstation", "Workstation"


class AgentPlat(models.TextChoices):
    WINDOWS = "windows", "Windows"
    LINUX = "linux", "Linux"
    DARWIN = "darwin", "macOS"


class ClientTreeSort(models.TextChoices):
    ALPHA_FAIL = "alphafail", "Move failing clients to the top"
    ALPHA = "alpha", "Sort alphabetically"


class AgentTableTabs(models.TextChoices):
    SERVER = "server", "Servers"
    WORKSTATION = "workstation", "Workstations"
    MIXED = "mixed", "Mixed"


class AgentDblClick(models.TextChoices):
    EDIT_AGENT = "editagent", "Edit Agent"
    TAKE_CONTROL = "takecontrol", "Take Control"
    REMOTE_BG = "remotebg", "Remote Background"
    URL_ACTION = "urlaction", "URL Action"


class ScriptShell(models.TextChoices):
    POWERSHELL = "powershell", "Powershell"
    CMD = "cmd", "Batch (CMD)"
    PYTHON = "python", "Python"
    SHELL = "shell", "Shell"
    NUSHELL = "nushell", "Nushell"
    DENO = "deno", "Deno"


class ScriptType(models.TextChoices):
    USER_DEFINED = "userdefined", "User Defined"
    BUILT_IN = "builtin", "Built In"


class EvtLogNames(models.TextChoices):
    APPLICATION = "Application", "Application"
    SYSTEM = "System", "System"
    SECURITY = "Security", "Security"


class EvtLogTypes(models.TextChoices):
    INFO = "INFO", "Information"
    WARNING = "WARNING", "Warning"
    ERROR = "ERROR", "Error"
    AUDIT_SUCCESS = "AUDIT_SUCCESS", "Success Audit"
    AUDIT_FAILURE = "AUDIT_FAILURE", "Failure Audit"


class EvtLogFailWhen(models.TextChoices):
    CONTAINS = "contains", "Log contains"
    NOT_CONTAINS = "not_contains", "Log does not contain"


class CheckStatus(models.TextChoices):
    PASSING = "passing", "Passing"
    FAILING = "failing", "Failing"
    PENDING = "pending", "Pending"


class PAStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"


class PAAction(models.TextChoices):
    SCHED_REBOOT = "schedreboot", "Scheduled Reboot"
    AGENT_UPDATE = "agentupdate", "Agent Update"
    CHOCO_INSTALL = "chocoinstall", "Chocolatey Software Install"
    RUN_CMD = "runcmd", "Run Command"
    RUN_SCRIPT = "runscript", "Run Script"
    RUN_PATCH_SCAN = "runpatchscan", "Run Patch Scan"
    RUN_PATCH_INSTALL = "runpatchinstall", "Run Patch Install"


class CheckType(models.TextChoices):
    DISK_SPACE = "diskspace", "Disk Space Check"
    PING = "ping", "Ping Check"
    CPU_LOAD = "cpuload", "CPU Load Check"
    MEMORY = "memory", "Memory Check"
    WINSVC = "winsvc", "Service Check"
    SCRIPT = "script", "Script Check"
    EVENT_LOG = "eventlog", "Event Log Check"


class AuditActionType(models.TextChoices):
    LOGIN = "login", "User Login"
    FAILED_LOGIN = "failed_login", "Failed User Login"
    DELETE = "delete", "Delete Object"
    MODIFY = "modify", "Modify Object"
    ADD = "add", "Add Object"
    VIEW = "view", "View Object"
    CHECK_RUN = "check_run", "Check Run"
    TASK_RUN = "task_run", "Task Run"
    AGENT_INSTALL = "agent_install", "Agent Install"
    REMOTE_SESSION = "remote_session", "Remote Session"
    EXEC_SCRIPT = "execute_script", "Execute Script"
    EXEC_COMMAND = "execute_command", "Execute Command"
    BULK_ACTION = "bulk_action", "Bulk Action"
    URL_ACTION = "url_action", "URL Action"


class AuditObjType(models.TextChoices):
    USER = "user", "User"
    SCRIPT = "script", "Script"
    AGENT = "agent", "Agent"
    POLICY = "policy", "Policy"
    WINUPDATE = "winupdatepolicy", "Patch Policy"
    CLIENT = "client", "Client"
    SITE = "site", "Site"
    CHECK = "check", "Check"
    AUTOTASK = "automatedtask", "Automated Task"
    CORE = "coresettings", "Core Settings"
    BULK = "bulk", "Bulk"
    ALERT_TEMPLATE = "alerttemplate", "Alert Template"
    ROLE = "role", "Role"
    URL_ACTION = "urlaction", "URL Action"
    KEYSTORE = "keystore", "Global Key Store"
    CUSTOM_FIELD = "customfield", "Custom Field"


class DebugLogLevel(models.TextChoices):
    INFO = "info", "Info"
    WARN = "warning", "Warning"
    ERROR = "error", "Error"
    CRITICAL = "critical", "Critical"


class DebugLogType(models.TextChoices):
    AGENT_UPDATE = "agent_update", "Agent Update"
    AGENT_ISSUES = "agent_issues", "Agent Issues"
    WIN_UPDATES = "win_updates", "Windows Updates"
    SYSTEM_ISSUES = "system_issues", "System Issues"
    SCRIPTING = "scripting", "Scripting"


class URLActionType(models.TextChoices):
    WEB = "web", "Web"
    REST = "rest", "Rest"


class URLActionRestMethod(models.TextChoices):
    GET = "get", "Get"
    POST = "post", "Post"
    PUT = "put", "Put"
    DELETE = "delete", "Delete"
    PATCH = "patch", "Patch"


# Agent db fields that are not needed for most queries, speeds up query
AGENT_DEFER = (
    "wmi_detail",
    "services",
    "created_by",
    "created_time",
    "modified_by",
    "modified_time",
)

AGENT_TABLE_DEFER = (
    "services",
    "created_by",
    "created_time",
    "modified_by",
    "modified_time",
)

ONLINE_AGENTS = (
    "pk",
    "agent_id",
    "last_seen",
    "overdue_time",
    "offline_time",
    "version",
)

FIELDS_TRIGGER_TASK_UPDATE_AGENT = [
    "run_time_bit_weekdays",
    "run_time_date",
    "expire_date",
    "daily_interval",
    "weekly_interval",
    "enabled",
    "remove_if_not_scheduled",
    "run_asap_after_missed",
    "monthly_days_of_month",
    "monthly_months_of_year",
    "monthly_weeks_of_month",
    "task_repetition_duration",
    "task_repetition_interval",
    "stop_task_at_duration_end",
    "random_task_delay",
    "run_asap_after_missed",
    "task_instance_policy",
]

POLICY_TASK_FIELDS_TO_COPY = [
    "alert_severity",
    "email_alert",
    "text_alert",
    "dashboard_alert",
    "name",
    "actions",
    "run_time_bit_weekdays",
    "run_time_date",
    "expire_date",
    "daily_interval",
    "weekly_interval",
    "task_type",
    "enabled",
    "remove_if_not_scheduled",
    "run_asap_after_missed",
    "custom_field",
    "collector_all_output",
    "monthly_days_of_month",
    "monthly_months_of_year",
    "monthly_weeks_of_month",
    "task_repetition_duration",
    "task_repetition_interval",
    "stop_task_at_duration_end",
    "random_task_delay",
    "run_asap_after_missed",
    "task_instance_policy",
    "continue_on_error",
]

CHECKS_NON_EDITABLE_FIELDS = [
    "check_type",
    "overridden_by_policy",
    "created_by",
    "created_time",
    "modified_by",
    "modified_time",
]

POLICY_CHECK_FIELDS_TO_COPY = [
    "check_type",
    "warning_threshold",
    "error_threshold",
    "alert_severity",
    "name",
    "run_interval",
    "disk",
    "fails_b4_alert",
    "ip",
    "script",
    "script_args",
    "info_return_codes",
    "warning_return_codes",
    "timeout",
    "svc_name",
    "svc_display_name",
    "svc_policy_mode",
    "pass_if_start_pending",
    "pass_if_svc_not_exist",
    "restart_if_stopped",
    "log_name",
    "event_id",
    "event_id_is_wildcard",
    "event_type",
    "event_source",
    "event_message",
    "fail_when",
    "search_last_days",
    "number_of_events_b4_alert",
    "email_alert",
    "text_alert",
    "dashboard_alert",
]


WEEK_DAYS = {
    "Sunday": 0x1,
    "Monday": 0x2,
    "Tuesday": 0x4,
    "Wednesday": 0x8,
    "Thursday": 0x10,
    "Friday": 0x20,
    "Saturday": 0x40,
}

MONTHS = {
    "January": 0x1,
    "February": 0x2,
    "March": 0x4,
    "April": 0x8,
    "May": 0x10,
    "June": 0x20,
    "July": 0x40,
    "August": 0x80,
    "September": 0x100,
    "October": 0x200,
    "November": 0x400,
    "December": 0x800,
}

WEEKS = {
    "First Week": 0x1,
    "Second Week": 0x2,
    "Third Week": 0x4,
    "Fourth Week": 0x8,
    "Last Week": 0x10,
}

MONTH_DAYS = {f"{b}": 0x1 << a for a, b in enumerate(range(1, 32))}
MONTH_DAYS["Last Day"] = 0x80000000

DEMO_NOT_ALLOWED = [
    {"name": "AgentProcesses", "methods": ["DELETE"]},
    {"name": "AgentMeshCentral", "methods": ["GET", "POST"]},
    {"name": "update_agents", "methods": ["POST"]},
    {"name": "send_raw_cmd", "methods": ["POST"]},
    {"name": "install_agent", "methods": ["POST"]},
    {"name": "GenerateAgent", "methods": ["GET"]},
    {"name": "email_test", "methods": ["POST"]},
    {"name": "server_maintenance", "methods": ["POST"]},
    {"name": "CodeSign", "methods": ["PATCH", "POST"]},
    {"name": "TwilioSMSTest", "methods": ["POST"]},
    {"name": "GetEditActionService", "methods": ["PUT", "POST"]},
    {"name": "TestScript", "methods": ["POST"]},
    {"name": "GetUpdateDeleteAgent", "methods": ["DELETE"]},
    {"name": "Reboot", "methods": ["POST", "PATCH"]},
    {"name": "recover", "methods": ["POST"]},
    {"name": "run_script", "methods": ["POST"]},
    {"name": "bulk", "methods": ["POST"]},
    {"name": "WMI", "methods": ["POST"]},
    {"name": "PolicyAutoTask", "methods": ["POST"]},
    {"name": "RunAutoTask", "methods": ["POST"]},
    {"name": "run_checks", "methods": ["POST"]},
    {"name": "GetSoftware", "methods": ["POST", "PUT"]},
    {"name": "ScanWindowsUpdates", "methods": ["POST"]},
    {"name": "InstallWindowsUpdates", "methods": ["POST"]},
    {"name": "PendingActions", "methods": ["DELETE"]},
    {"name": "clear_cache", "methods": ["GET"]},
    {"name": "ResetPass", "methods": ["PUT"]},
    {"name": "Reset2FA", "methods": ["PUT"]},
    {"name": "bulk_run_checks", "methods": ["GET"]},
    {"name": "OpenAICodeCompletion", "methods": ["POST"]},
    {"name": "wol", "methods": ["POST"]},
]

CONFIG_MGMT_CMDS = (
    "api",
    "version",
    "webversion",
    "meshver",
    "natsver",
    "frontend",
    "webdomain",
    "djangoadmin",
    "setuptoolsver",
    "wheelver",
    "dbname",
    "dbuser",
    "dbhost",
    "dbpw",
    "dbport",
    "meshsite",
    "meshuser",
    "meshtoken",
    "meshdomain",
    "certfile",
    "keyfile",
)

ALL_TIMEZONES = sorted(zoneinfo.available_timezones())
