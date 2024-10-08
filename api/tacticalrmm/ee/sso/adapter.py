from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from allauth.account.utils import user_email, user_field, user_username
from allauth.utils import valid_email_or_none

from accounts.models import Role
class TacticalSocialAdapter(DefaultSocialAccountAdapter):
    
    def populate_user(self, request, sociallogin, data):
        """
        Hook that can be used to further populate the user instance.

        For convenience, we populate several common fields.

        Note that the user instance being populated represents a
        suggested User instance that represents the social user that is
        in the process of being logged in.

        The User instance need not be completely valid and conflict
        free. For example, verifying whether or not the username
        already exists, is not a responsibility.
        """
        username = data.get("username")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        name = data.get("name")
        user = sociallogin.user
        user_username(user, username or "")
        user_email(user, valid_email_or_none(email) or "")
        name_parts = (name or "").partition(" ")
        user_field(user, "first_name", first_name or name_parts[0])
        user_field(user, "last_name", last_name or name_parts[2])


        try:
            provider = sociallogin.account.get_provider()
            provider_settings = SocialApp.objects.get(provider_id=provider).settings
            user.role = Role.objects.get(pk=provider_settings["role"])
            print(provider, provider_settings)
        except:
            print("Provider settings or Role not found. Continuing with blank permissions.")
        return user