from django.conf import settings
from django.core.management.base import BaseCommand
from scripts.models import Script


class Command(BaseCommand):
    help = "loads scripts for demo"

    def handle(self, *args, **kwargs):
        scripts_dir = settings.BASE_DIR.joinpath("tacticalrmm/test_data/demo_scripts")
        scripts = Script.objects.filter(script_type="userdefined")
        for script in scripts:
            filepath = scripts_dir.joinpath(script.filename)
            with open(filepath, "rb") as f:
                script.script_body = f.read().decode("utf-8")
                script.save(update_fields=["script_body"])

        self.stdout.write(self.style.SUCCESS("Added userdefined scripts"))
