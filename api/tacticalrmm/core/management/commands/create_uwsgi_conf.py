import math
import multiprocessing
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = "Creates a systemd service file for uWSGI"

    def handle(self, *args, **options):
        cpu_count = multiprocessing.cpu_count()

        # Set initial defaults for low-spec machines
        if cpu_count <= 2:
            cpu_count = 4
            worker_initial = 2

        # Detect total RAM in GB
        try:
            with open("/proc/meminfo", "r") as meminfo:
                for line in meminfo:
                    if line.startswith("MemTotal:"):
                        mem_total_kb = int(line.split()[1])
                        ram = math.ceil(
                            mem_total_kb / (1024 * 1024)
                        )  # Convert KB to GB
                        break

            # Adjust max_requests and max_workers based on RAM
            if ram <= 4:
                # Small systems (<= 4GB): conservative settings
                max_requests = 500
                max_workers = cpu_count
            elif ram <= 8:
                # Medium systems (4-8GB): balanced settings
                max_requests = 1000
                max_workers = cpu_count * 2
            else:
                # Larger systems (>8GB): aggressive settings
                max_requests = 2000
                max_workers = cpu_count * 3

        except FileNotFoundError:
            # Fallback for systems without /proc/meminfo (e.g., non-Linux)
            ram = 4  # Assume a conservative default
            max_requests = 500
            max_workers = cpu_count

        # Paths
        if os.environ.get("TACTICAL_DEV"):
            home = str(settings.BASE_DIR.parents[0] / "env")
            socket = str(settings.BASE_DIR / "tacticalrmm.sock")

        # Optimized settings based on machine specs
        threads = 4 if cpu_count <= 8 else 3  # 4 threads for <= 8 CPUs, 3 for > 8 CPUs
        cheaper = worker_initial  # Cheaper matches initial workers
        socket_timeout = 600  # Increased timeout for high load stability
        harakiri = 900  # Longer harakiri to handle peak loads

        config = {}
        config["uwsgi"] = {
            "chdir": str(settings.BASE_DIR),
            "module": "tacticalrmm.wsgi",
            "home": home,
            "master": str(getattr(settings, "UWSGI_MASTER", True)).lower(),
            "enable-threads": str(
                getattr(settings, "UWSGI_ENABLE_THREADS", True)
            ).lower(),
            "socket": socket,
            "harakiri": str(
                harakiri
            ),  # Time (seconds) before killing unresponsive workers
            "chmod-socket": str(getattr(settings, "UWSGI_CHMOD_SOCKET", 660)),
            "buffer-size": str(getattr(settings, "UWSGI_BUFFER_SIZE", 65535)),
            "vacuum": str(getattr(settings, "UWSGI_VACUUM", True)).lower(),
            "die-on-term": str(getattr(settings, "UWSGI_DIE_ON_TERM", True)).lower(),
            "max-requests": str(
                max_requests
            ),  # Recycle workers after this many requests
            "disable-logging": str(
                getattr(settings, "UWSGI_DISABLE_LOGGING", True)
            ).lower(),
            "worker-reload-mercy": str(getattr(settings, "UWSGI_RELOAD_MERCY", 30)),
            "cheaper-algo": "busyness",  # Use busyness algorithm for dynamic scaling
            "cheaper": str(cheaper),  # Minimum active workers
            "cheaper-initial": str(worker_initial),  # Initial active workers
            "workers": str(max_workers),  # Maximum worker processes
            "threads": str(threads),  # Threads per worker, optimized for CPU count
            "cheaper-step": str(2),  # Add/remove 2 workers at a time
            "cheaper-overload": str(1),  # React to overload in 1 second
            "cheaper-busyness-min": str(20),  # Scale up if busyness < 20%
            "cheaper-busyness-max": str(50),  # Scale down if busyness > 50%
            "socket-timeout": str(
                socket_timeout
            ),  # Socket timeout for high concurrency
        }

        # Add debug options if enabled
        if getattr(settings, "UWSGI_DEBUG", False):
            config["uwsgi"]["stats"] = "/tmp/stats.socket"

        # Render and write the config file (assuming this part exists in the original)
        # If this part is missing in your diff, let me know, and I’ll adjust accordingly!
        uwsgi_conf = render_to_string("uwsgi.ini", config)
        with open("uwsgi.ini", "w") as f:
            f.write(uwsgi_conf)

        self.stdout.write(self.style.SUCCESS("uWSGI configuration created successfully"))
