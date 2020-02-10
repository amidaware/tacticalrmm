from django.core.management.base import BaseCommand
from knox.models import AuthToken


class Command(BaseCommand):
    help = "Deletes all knox tokens"

    def handle(self, *args, **kwargs):
        AuthToken.objects.all().delete()
        self.stdout.write("All tokens have been deleted!")
