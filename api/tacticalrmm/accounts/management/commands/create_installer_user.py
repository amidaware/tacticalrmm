import uuid

from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Creates the installer user"

    def handle(self, *args, **kwargs):
        if User.objects.filter(is_installer_user=True).exists():
            return

        User.objects.create_user(  # type: ignore
            username=uuid.uuid4().hex,
            is_installer_user=True,
            password=User.objects.make_random_password(60),  # type: ignore
        )
