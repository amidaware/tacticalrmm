from django.contrib.auth.models import AbstractUser
from django.db import models

from logs.models import BaseAuditModel

AGENT_DBLCLICK_CHOICES = [
    ("editagent", "Edit Agent"),
    ("takecontrol", "Take Control"),
    ("remotebg", "Remote Background"),
    ("urlaction", "URL Action"),
]

AGENT_TBL_TAB_CHOICES = [
    ("server", "Servers"),
    ("workstation", "Workstations"),
    ("mixed", "Mixed"),
]

CLIENT_TREE_SORT_CHOICES = [
    ("alphafail", "Move failing clients to the top"),
    ("alpha", "Sort alphabetically"),
]


class User(AbstractUser, BaseAuditModel):
    is_active = models.BooleanField(default=True)
    totp_key = models.CharField(max_length=50, null=True, blank=True)
    dark_mode = models.BooleanField(default=True)
    show_community_scripts = models.BooleanField(default=True)
    agent_dblclick_action = models.CharField(
        max_length=50, choices=AGENT_DBLCLICK_CHOICES, default="editagent"
    )
    url_action = models.ForeignKey(
        "core.URLAction",
        related_name="user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    default_agent_tbl_tab = models.CharField(
        max_length=50, choices=AGENT_TBL_TAB_CHOICES, default="server"
    )
    agents_per_page = models.PositiveIntegerField(default=50)  # not currently used
    client_tree_sort = models.CharField(
        max_length=50, choices=CLIENT_TREE_SORT_CHOICES, default="alphafail"
    )
    client_tree_splitter = models.PositiveIntegerField(default=11)
    loading_bar_color = models.CharField(max_length=255, default="red")
    clear_search_when_switching = models.BooleanField(default=True)
    is_installer_user = models.BooleanField(default=False)

    agent = models.OneToOneField(
        "agents.Agent",
        related_name="user",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    role = models.ForeignKey(
        "accounts.Role",
        null=True,
        blank=True,
        related_name="roles",
        on_delete=models.SET_NULL,
    )

    @staticmethod
    def serialize(user):
        # serializes the task and returns json
        from .serializers import UserSerializer

        return UserSerializer(user).data


class Role(models.Model):
    name = models.CharField(max_length=255, unique=True)
    is_superuser = models.BooleanField(default=False)

    # agents
    can_use_mesh = models.BooleanField(default=False)
    can_uninstall_agents = models.BooleanField(default=False)
    can_update_agents = models.BooleanField(default=False)
    can_edit_agent = models.BooleanField(default=False)
    can_manage_procs = models.BooleanField(default=False)
    can_view_eventlogs = models.BooleanField(default=False)
    can_send_cmd = models.BooleanField(default=False)
    can_reboot_agents = models.BooleanField(default=False)
    can_install_agents = models.BooleanField(default=False)
    can_run_scripts = models.BooleanField(default=False)
    can_run_bulk = models.BooleanField(default=False)

    # core
    can_manage_notes = models.BooleanField(default=False)
    can_view_core_settings = models.BooleanField(default=False)
    can_edit_core_settings = models.BooleanField(default=False)
    can_do_server_maint = models.BooleanField(default=False)
    can_code_sign = models.BooleanField(default=False)

    # checks
    can_manage_checks = models.BooleanField(default=False)
    can_run_checks = models.BooleanField(default=False)

    # clients
    can_manage_clients = models.BooleanField(default=False)
    can_manage_sites = models.BooleanField(default=False)
    can_manage_deployments = models.BooleanField(default=False)

    # automation
    can_manage_automation_policies = models.BooleanField(default=False)

    # automated tasks
    can_manage_autotasks = models.BooleanField(default=False)
    can_run_autotasks = models.BooleanField(default=False)

    # logs
    can_view_auditlogs = models.BooleanField(default=False)
    can_manage_pendingactions = models.BooleanField(default=False)
    can_view_debuglogs = models.BooleanField(default=False)

    # scripts
    can_manage_scripts = models.BooleanField(default=False)

    # alerts
    can_manage_alerts = models.BooleanField(default=False)

    # win services
    can_manage_winsvcs = models.BooleanField(default=False)

    # software
    can_manage_software = models.BooleanField(default=False)

    # windows updates
    can_manage_winupdates = models.BooleanField(default=False)

    # accounts
    can_manage_accounts = models.BooleanField(default=False)
    can_manage_roles = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @staticmethod
    def perms():
        return [
            "is_superuser",
            "can_use_mesh",
            "can_uninstall_agents",
            "can_update_agents",
            "can_edit_agent",
            "can_manage_procs",
            "can_view_eventlogs",
            "can_send_cmd",
            "can_reboot_agents",
            "can_install_agents",
            "can_run_scripts",
            "can_run_bulk",
            "can_manage_notes",
            "can_view_core_settings",
            "can_edit_core_settings",
            "can_do_server_maint",
            "can_code_sign",
            "can_manage_checks",
            "can_run_checks",
            "can_manage_clients",
            "can_manage_sites",
            "can_manage_deployments",
            "can_manage_automation_policies",
            "can_manage_autotasks",
            "can_run_autotasks",
            "can_view_auditlogs",
            "can_manage_pendingactions",
            "can_view_debuglogs",
            "can_manage_scripts",
            "can_manage_alerts",
            "can_manage_winsvcs",
            "can_manage_software",
            "can_manage_winupdates",
            "can_manage_accounts",
            "can_manage_roles",
        ]
