"""
Copyright (c) 2024-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp

from accounts.models import Role


class TacticalSocialAdapter(DefaultSocialAccountAdapter):

    def populate_user(self, request, sociallogin, data):

        user = super().populate_user(request, sociallogin, data)
        try:
            provider = sociallogin.account.get_provider()
            provider_settings = SocialApp.objects.get(provider_id=provider).settings
            user.role = Role.objects.get(pk=provider_settings["role"])
        except:
            print(
                "Provider settings or Role not found. Continuing with blank permissions."
            )
        return user
