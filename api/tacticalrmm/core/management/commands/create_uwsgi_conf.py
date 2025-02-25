import configparser
import math
import multiprocessing
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate conf for uwsgi"

    def handle(self, *args, **kwargs):
        self.stdout.write("Creating uwsgi conf...")

        # Detect CPU count
        try:
            cpu_count = multiprocessing.cpu_count()
            # Initial workers set to ~33% of CPU count, with a minimum of 2
            worker_initial = max(cpu_count // 3, 2)
        except Exception:
            # Fallback to 4 CPUs if detection fails
            cpu_count = 4
            worker_initial = 2

        # Detect total RAM in GB
        try:
            with open('/proc/meminfo', 'r') as meminfo:
                for line in meminfo:
                    if line.startswith('MemTotal:'):
                        mem_total_kb = int(line.split()[1])
                        ram = math.ceil(mem_total_kb / (1024 * 1024))  # Convert KB to GB
                        break

            # Adjust max_requests and max_workers based on RAM
            if ram <= 4:
                # Small systems (<= 4GB): conservative settings
                max_requests = 500
                max_workers = min(cpu_count * 4, 20)  # Up to 4 workers per CPU, max 20
            elif ram <= 8:
                # Medium systems (4-8GB): balanced settings
                max_requests = 2000
                max_workers = min(cpu_count * 6, 40)  # Up to 6 workers per CPU, max 40
            else:
                # Large systems (>8GB): aggressive settings for high load
                max_requests = 5000
                max_workers = min(cpu_count * 8, 80)  # Up to 8 workers per CPU, max 80
        except Exception:
            # Fallback to safe defaults if RAM detection fails
            max_requests = 1000
            max_workers = 10

        # Create configuration object
        config = configparser.ConfigParser()

        # Determine home and socket based on environment
        if getattr(settings, "DOCKER_BUILD", False):
            home = str(Path(os.getenv("VIRTUAL_ENV")))
            socket = "0.0.0.0:8080"
        else:
            home = str(settings.BASE_DIR.parents[0] / "env")
            socket = str(settings.BASE_DIR / "tacticalrmm.sock")

        # Optimized settings based on machine specs
        threads = 4 if cpu_count <= 8 else 3  # 4 threads for <= 8 CPUs, 3 for > 8 CPUs
        cheaper = worker_initial              # Cheaper matches initial workers
        socket_timeout = 600                  # Increased timeout for high load stability
        harakiri = 900                        # Longer harakiri to handle peak loads

        config["uwsgi"] = {
            "chdir": str(settings.BASE_DIR),
            "module": "tacticalrmm.wsgi",
            "home": home,
            "master": str(getattr(settings, "UWSGI_MASTER", True)).lower(),
            "enable-threads": str(getattr(settings, "UWSGI_ENABLE_THREADS", True)).lower(),
            "socket": socket,
            "harakiri": str(harakiri),  # Time (seconds) before killing unresponsive workers
            "chmod-socket": str(getattr(settings, "UWSGI_CHMOD_SOCKET", 660)),
            "buffer-size": str(getattr(settings, "UWSGI_BUFFER_SIZE", 65535)),
            "vacuum": str(getattr(settings, "UWSGI_VACUUM", True)).lower(),
            "die-on-term": str(getattr(settings, "UWSGI_DIE_ON_TERM", True)).lower(),
            "max-requests": str(max_requests),  # Recycle workers after this many requests
            "disable-logging": str(getattr(settings, "UWSGI_DISABLE_LOGGING", True)).lower(),
            "worker-reload-mercy": str(getattr(settings, "UWSGI_RELOAD_MERCY", 30)),
            "cheaper-algo": "busyness",  # Use busyness algorithm for dynamic scaling
            "cheaper": str(cheaper),     # Minimum active workers
            "cheaper-initial": str(worker_initial),  # Initial active workers
            "workers": str(max_workers),  # Maximum worker processes
            "threads": str(threads),      # Threads per worker, optimized for CPU count
            "cheaper-step": str(2),       # Add/remove 2 workers at a time
            "cheaper-overload": str(1),   # React to overload in 1 second
            "cheaper-busyness-min": str(20),  # Scale up if busyness < 20%
            "cheaper-busyness-max": str(50),  # Scale down if busyness > 50%
            "socket-timeout": str(socket_timeout),  # Socket timeout for high concurrency
        }

        # Add debug options if enabled
        if getattr(settings, "UWSGI_DEBUG", False):
            config["uwsgi"]["stats"] = "/tmp/stats.socket"
            config["uwsgi"]["cheaper-busyness-verbose"] = str(True).lower()

        # Write the configuration to app.ini
        with open(settings.BASE_DIR / "app.ini", "w") as fp:
            config.write(fp)

        self.stdout.write("Created uwsgi conf")
