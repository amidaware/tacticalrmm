from django.db import models
from django.contrib.auth.models import AbstractUser

from logs.models import BaseAuditModel

AGENT_DBLCLICK_CHOICES = [
    ("editagent", "Edit Agent"),
    ("takecontrol", "Take Control"),
    ("remotebg", "Remote Background"),
]


class User(AbstractUser, BaseAuditModel):
    is_active = models.BooleanField(default=True)
    totp_key = models.CharField(max_length=50, null=True, blank=True)
    dark_mode = models.BooleanField(default=True)
    show_community_scripts = models.BooleanField(default=True)
    agent_dblclick_action = models.CharField(
        max_length=50, choices=AGENT_DBLCLICK_CHOICES, default="editagent"
    )

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
