import os
import json

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Generate conf for nats-api"

    def handle(self, *args, **kwargs):

        self.stdout.write("Creating configuration for nats-api...")
        db = settings.DATABASES["default"]
        config = {
            "key": settings.SECRET_KEY,
            "natsurl": f"tls://{settings.ALLOWED_HOSTS[0]}:4222",
            "user": db["USER"],
            "pass": db["PASSWORD"],
            "host": db["HOST"],
            "port": int(db["PORT"]),
            "dbname": db["NAME"],
        }
        conf = os.path.join(settings.BASE_DIR, "nats-api.conf")
        with open(conf, "w") as f:
            json.dump(config, f)

        self.stdout.write("Configuration for nats-api created successfully")
