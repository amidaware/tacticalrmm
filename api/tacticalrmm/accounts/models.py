from django.contrib.auth.models import AbstractUser
from django.db import models

from logs.models import BaseAuditModel

AGENT_DBLCLICK_CHOICES = [
    ("editagent", "Edit Agent"),
    ("takecontrol", "Take Control"),
    ("remotebg", "Remote Background"),
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
    default_agent_tbl_tab = models.CharField(
        max_length=50, choices=AGENT_TBL_TAB_CHOICES, default="server"
    )
    agents_per_page = models.PositiveIntegerField(default=50)  # not currently used
    client_tree_sort = models.CharField(
        max_length=50, choices=CLIENT_TREE_SORT_CHOICES, default="alphafail"
    )
    client_tree_splitter = models.PositiveIntegerField(default=11)
    loading_bar_color = models.CharField(max_length=255, default="red")

    agent = models.OneToOneField(
        "agents.Agent",
        related_name="user",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    @staticmethod
    def serialize(user):
        # serializes the task and returns json
        from .serializers import UserSerializer

        return UserSerializer(user).data
