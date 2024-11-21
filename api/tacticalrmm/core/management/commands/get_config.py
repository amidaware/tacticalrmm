from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand

from tacticalrmm.util_settings import get_backend_url, get_root_domain, get_webdomain
from tacticalrmm.utils import get_certs


class Command(BaseCommand):
    help = "Get config vars to be used in shell scripts"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str, help="The name of the config")

    def handle(self, *args, **kwargs):
        match kwargs["name"]:
            case "api":
                self.stdout.write(settings.ALLOWED_HOSTS[0])
            case "rootdomain":
                self.stdout.write(get_root_domain(settings.ALLOWED_HOSTS[0]))
            case "version":
                self.stdout.write(settings.TRMM_VERSION)
            case "webversion":
                self.stdout.write(settings.WEB_VERSION)
            case "meshver":
                self.stdout.write(settings.MESH_VER)
            case "natsver":
                self.stdout.write(settings.NATS_SERVER_VER)
            case "frontend":
                self.stdout.write(settings.CORS_ORIGIN_WHITELIST[0])
            case "backend_url":
                self.stdout.write(
                    get_backend_url(
                        settings.ALLOWED_HOSTS[0],
                        settings.TRMM_PROTO,
                        settings.TRMM_BACKEND_PORT,
                    )
                )
            case "webdomain":
                self.stdout.write(get_webdomain(settings.CORS_ORIGIN_WHITELIST[0]))
            case "djangoadmin":
                url = f"https://{settings.ALLOWED_HOSTS[0]}/{settings.ADMIN_URL}"
                self.stdout.write(url)
            case "setuptoolsver":
                self.stdout.write(settings.SETUPTOOLS_VER)
            case "wheelver":
                self.stdout.write(settings.WHEEL_VER)
            case "dbname":
                self.stdout.write(settings.DATABASES["default"]["NAME"])
            case "dbuser":
                self.stdout.write(settings.DATABASES["default"]["USER"])
            case "dbpw":
                self.stdout.write(settings.DATABASES["default"]["PASSWORD"])
            case "dbhost":
                self.stdout.write(settings.DATABASES["default"]["HOST"])
            case "dbport":
                self.stdout.write(settings.DATABASES["default"]["PORT"])
            case "meshsite" | "meshuser" | "meshtoken" | "meshdomain":
                from core.models import CoreSettings

                core: "CoreSettings" = CoreSettings.objects.first()
                if kwargs["name"] == "meshsite":
                    obj = core.mesh_site
                elif kwargs["name"] == "meshuser":
                    obj = core.mesh_username
                elif kwargs["name"] == "meshdomain":
                    obj = urlparse(core.mesh_site).netloc
                else:
                    obj = core.mesh_token

                self.stdout.write(obj)
            case "certfile" | "keyfile":
                crt, key = get_certs()
                if kwargs["name"] == "certfile":
                    self.stdout.write(crt)
                elif kwargs["name"] == "keyfile":
                    self.stdout.write(key)
