import os
import subprocess

import pyotp
from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Reset 2fa"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)

    def handle(self, *args, **kwargs):
        username = kwargs["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} doesn't exist"))
            return

        domain = "Tactical RMM"
        nginx = "/etc/nginx/sites-available/frontend.conf"
        found = None
        if os.path.exists(nginx):
            try:
                with open(nginx, "r") as f:
                    for line in f:
                        if "server_name" in line:
                            found = line
                            break

                if found:
                    rep = found.replace("server_name", "").replace(";", "")
                    domain = "".join(rep.split())
            except:
                pass

        code = pyotp.random_base32()
        user.totp_key = code
        user.save(update_fields=["totp_key"])

        url = pyotp.totp.TOTP(code).provisioning_uri(username, issuer_name=domain)
        subprocess.run(f'qr "{url}"', shell=True)
        self.stdout.write(
            self.style.WARNING("Scan the barcode above with your authenticator app")
        )
        self.stdout.write(
            self.style.WARNING(
                f"If that doesn't work you may manually enter the setup key: {code}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f"2fa was successfully reset for user {username}")
        )
