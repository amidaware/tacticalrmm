from django.core.management.base import BaseCommand

from core.tasks import sync_mesh_perms_task


class Command(BaseCommand):
    help = "Sync mesh users/perms with trmm users/perms"

    def handle(self, *args, **kwargs):
        self.stdout.write(
            self.style.SUCCESS(
                "Syncing trmm users/permissions with meshcentral, this might take a long time...please wait..."
            )
        )
        sync_mesh_perms_task()
