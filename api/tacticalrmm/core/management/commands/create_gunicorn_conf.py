import multiprocessing

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate conf for gunicorn"

    def handle(self, *args, **kwargs):
        self.stdout.write("Creating gunicorn conf...")

        cpu_count = multiprocessing.cpu_count()

        # worker processes
        workers = getattr(settings, "TRMM_GUNICORN_WORKERS", cpu_count * 2 + 1)
        threads = getattr(settings, "TRMM_GUNICORN_THREADS", cpu_count * 2)
        worker_class = getattr(settings, "TRMM_GUNICORN_WORKER_CLASS", "gthread")
        max_requests = getattr(settings, "TRMM_GUNICORN_MAX_REQUESTS", 50)
        max_requests_jitter = getattr(settings, "TRMM_GUNICORN_MAX_REQUESTS_JITTER", 8)
        worker_connections = getattr(settings, "TRMM_GUNICORN_WORKER_CONNS", 1000)
        timeout = getattr(settings, "TRMM_GUNICORN_TIMEOUT", 300)
        graceful_timeout = getattr(settings, "TRMM_GUNICORN_GRACEFUL_TIMEOUT", 300)

        # socket
        backlog = getattr(settings, "TRMM_GUNICORN_BACKLOG", 2048)
        if getattr(settings, "DOCKER_BUILD", False):
            bind = "0.0.0.0:8080"
        else:
            bind = f"unix:{settings.BASE_DIR / 'tacticalrmm.sock'}"

        # security
        limit_request_line = getattr(settings, "TRMM_GUNICORN_LIMIT_REQUEST_LINE", 0)
        limit_request_fields = getattr(
            settings, "TRMM_GUNICORN_LIMIT_REQUEST_FIELDS", 500
        )
        limit_request_field_size = getattr(
            settings, "TRMM_GUNICORN_LIMIT_REQUEST_FIELD_SIZE", 0
        )

        # server
        preload_app = getattr(settings, "TRMM_GUNICORN_PRELOAD_APP", True)

        # log
        loglevel = getattr(settings, "TRMM_GUNICORN_LOGLEVEL", "info")

        cfg = [
            f"bind = '{bind}'",
            f"workers = {workers}",
            f"threads = {threads}",
            f"worker_class = '{worker_class}'",
            f"backlog = {backlog}",
            f"worker_connections = {worker_connections}",
            f"timeout = {timeout}",
            f"graceful_timeout = {graceful_timeout}",
            f"limit_request_line = {limit_request_line}",
            f"limit_request_fields = {limit_request_fields}",
            f"limit_request_field_size = {limit_request_field_size}",
            f"max_requests = {max_requests}",
            f"max_requests_jitter = {max_requests_jitter}",
            f"loglevel = '{loglevel}'",
            f"chdir = '{settings.BASE_DIR}'",
            f"preload_app = {preload_app}",
        ]

        with open(settings.BASE_DIR / "gunicorn_config.py", "w") as fp:
            for line in cfg:
                fp.write(line + "\n")

        self.stdout.write("Created gunicorn conf")
