from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Reset password for user"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)

    def handle(self, *args, **kwargs):
        username = kwargs["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User {username} doesn't exist"))
            return

        passwd = input("Enter new password: ")
        user.set_password(passwd)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Password for {username} was reset!"))
