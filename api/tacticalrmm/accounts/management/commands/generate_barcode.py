import pyotp
import subprocess
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generates barcode for Google Authenticator"

    def add_arguments(self, parser):
        parser.add_argument("code", type=str)
        parser.add_argument("username", type=str)

    def handle(self, *args, **kwargs):
        code = kwargs["code"]
        username = kwargs["username"]

        url = pyotp.totp.TOTP(code).provisioning_uri(
            username, issuer_name="Tactical RMM"
        )
        subprocess.run(f'qr "{url}"', shell=True)
        self.stdout.write(self.style.SUCCESS("Scan the barcode above with your google authenticator app"))
        self.stdout.write(self.style.SUCCESS(f"If that doesn't work you may manually enter the key: {code}"))
