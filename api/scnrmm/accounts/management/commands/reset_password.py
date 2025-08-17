from getpass import getpass

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

        pass1, pass2 = "foo", "bar"
        while pass1 != pass2:
            pass1 = getpass()
            pass2 = getpass(prompt="Confirm Password:")
            if pass1 != pass2:
                self.stdout.write(self.style.ERROR("Passwords don't match"))

        user.set_password(pass1)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Password for {username} was reset!"))
