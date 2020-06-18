from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    is_active = models.BooleanField(default=True)
    totp_key = models.CharField(max_length=50, null=True, blank=True)
