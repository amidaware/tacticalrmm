from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from allauth.account.utils import user_email, user_field, user_username
from allauth.utils import valid_email_or_none

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
