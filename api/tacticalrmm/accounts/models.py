from django.db import models
from django.contrib.auth.models import AbstractUser

from logs.models import BaseAuditModel


class User(AbstractUser, BaseAuditModel):
    is_active = models.BooleanField(default=True)
    totp_key = models.CharField(max_length=50, null=True, blank=True)
    dark_mode = models.BooleanField(default=True)

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
