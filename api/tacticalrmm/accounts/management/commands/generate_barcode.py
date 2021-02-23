import subprocess

import pyotp
from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Generates barcode for Authenticator and creates totp for user"

    def add_arguments(self, parser):
        parser.add_argument("code", type=str)
        parser.add_argument("username", type=str)
        parser.add_argument("domain", type=str)

    def handle(self, *args, **kwargs):
        code = kwargs["code"]
        username = kwargs["username"]
        domain = kwargs["domain"]

        user = User.objects.get(username=username)
        user.totp_key = code
        user.save(update_fields=["totp_key"])

        url = pyotp.totp.TOTP(code).provisioning_uri(username, issuer_name=domain)
        subprocess.run(f'qr "{url}"', shell=True)
        self.stdout.write(
            self.style.SUCCESS("Scan the barcode above with your authenticator app")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"If that doesn't work you may manually enter the setup key: {code}"
            )
        )
