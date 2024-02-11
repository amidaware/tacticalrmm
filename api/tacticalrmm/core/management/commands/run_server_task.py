from django.core.management.base import BaseCommand

from core.utils import run_server_task
class Command(BaseCommand):
    help = "Runs a server task"

    def add_arguments(self, parser):
        parser.add_argument(
            "--task-id",
            action="store_true",
            help="Server task id",
        )
    
    def handle(self, *args, **kwargs) -> None:
        task_id = kwargs["task-id"]

        try:
            output, _= run_server_task(server_task_id=task_id)
            self.style.SUCCESS(output)
        except Exception as error:
            self.style.ERROR(str(error))