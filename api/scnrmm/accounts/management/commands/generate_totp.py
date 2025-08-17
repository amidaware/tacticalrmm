import pyotp
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generates TOTP Random Base 32"

    def handle(self, *args, **kwargs):
        self.stdout.write(pyotp.random_base32())
