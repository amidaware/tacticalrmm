"""
Copyright (c) 2024-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import pyotp
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from django.core.exceptions import PermissionDenied

from accounts.models import Role
from core.tasks import sync_mesh_perms_task
from core.utils import token_is_valid
from tacticalrmm.logger import logger
from tacticalrmm.utils import get_core_settings


class TacticalSocialAdapter(DefaultSocialAccountAdapter):

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        try:
            provider = sociallogin.account.get_provider()
            provider_settings = SocialApp.objects.get(provider_id=provider).settings
            user.role = Role.objects.get(pk=provider_settings["role"])
        except Exception:
            logger.debug(
                "Provider settings or Role not found. Continuing with blank permissions."
            )
        user.totp_key = pyotp.random_base32()  # not actually used
        sync_mesh_perms_task.delay()
        return user

    def is_open_for_signup(self, request, sociallogin):
        _, valid = token_is_valid()
        if not valid:
            raise PermissionDenied()

        return super().is_open_for_signup(request, sociallogin)

    def list_providers(self, request):
        core_settings = get_core_settings()
        if not core_settings.sso_enabled:
            return []

        return super().list_providers(request)
