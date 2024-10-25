"""
Copyright (c) 2024-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from rest_framework import permissions
from allauth.socialaccount.models import SocialAccount


class SSOLoginPerms(permissions.BasePermission):
    def has_permission(self, r, view):
        return SocialAccount.objects.filter(user=r.user).exists()
