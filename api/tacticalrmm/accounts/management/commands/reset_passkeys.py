from django.core.management.base import BaseCommand

from accounts.models import User, WebAuthnCredential


class Command(BaseCommand):
    help = "Remove all passkeys for a user (TOTP remains as login fallback)"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)

    def handle(self, *args, **kwargs):
        username = kwargs["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} doesn't exist"))
            return

        count, _ = WebAuthnCredential.objects.filter(user=user).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {count} passkey(s) for user {username}. "
                "TOTP login remains available."
            )
        )
