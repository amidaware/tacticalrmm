from django.core.management.base import BaseCommand
from meshctrl.utils import get_login_token

from core.utils import get_core_settings


class Command(BaseCommand):
    help = "generate a url to login to mesh as the superuser"

    def handle(self, *args, **kwargs):

        core = get_core_settings()

        token = get_login_token(key=core.mesh_token, user=f"user//{core.mesh_username}")
        token_param = f"login={token}&"

        control = f"{core.mesh_site}/?{token_param}"

        self.stdout.write(self.style.SUCCESS(control))
