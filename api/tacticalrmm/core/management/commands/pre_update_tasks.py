from django.core.management.base import BaseCommand
from alerts.models import Alert


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, before migrations"

    def handle(self, *args, **kwargs):
        # adding this now for future updates
        Alert.objects.filter(agent=None).delete()
