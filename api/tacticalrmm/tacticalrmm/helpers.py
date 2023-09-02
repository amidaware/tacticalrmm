import random
import secrets
import string
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from cryptography import x509
from django.conf import settings
from django.utils import timezone as djangotime
from rest_framework import status
from rest_framework.response import Response

if TYPE_CHECKING:
    from datetime import datetime


def get_certs() -> tuple[str, str]:
    domain = settings.ALLOWED_HOSTS[0].split(".", 1)[1]
    cert_file = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    key_file = f"/etc/letsencrypt/live/{domain}/privkey.pem"

    if hasattr(settings, "CERT_FILE") and hasattr(settings, "KEY_FILE"):
        cert_file = settings.CERT_FILE
        key_file = settings.KEY_FILE

    return cert_file, key_file


def notify_error(msg: str) -> Response:
    return Response(msg, status=status.HTTP_400_BAD_REQUEST)


def get_nats_ports() -> tuple[int, int]:
    """
    Returns: tuple[nats_standard_port: int, nats_websocket_port: int]
    """
    nats_standard_port = getattr(settings, "NATS_STANDARD_PORT", 4222)
    nats_websocket_port = getattr(settings, "NATS_WEBSOCKET_PORT", 9235)

    return nats_standard_port, nats_websocket_port


def get_nats_internal_protocol() -> str:
    if getattr(settings, "TRMM_INSECURE", False):
        return "nats"

    return "tls"


def date_is_in_past(*, datetime_obj: "datetime", agent_tz: str) -> bool:
    """
    datetime_obj must be a naive datetime
    """
    # convert agent tz to UTC to compare
    localized = datetime_obj.replace(tzinfo=ZoneInfo(agent_tz))
    utc_time = localized.astimezone(ZoneInfo("UTC"))
    return djangotime.now() > utc_time


def get_webdomain() -> str:
    return urlparse(settings.CORS_ORIGIN_WHITELIST[0]).netloc


def rand_range(min: int, max: int) -> float:
    """
    Input is milliseconds.
    Returns float truncated to 2 decimals.
    """
    return round(random.uniform(min, max) / 1000, 2)


def setup_nats_options() -> dict[str, Any]:
    nats_std_port, _ = get_nats_ports()
    proto = get_nats_internal_protocol()
    opts = {
        "servers": f"{proto}://{settings.ALLOWED_HOSTS[0]}:{nats_std_port}",
        "user": "tacticalrmm",
        "name": "trmm-django",
        "password": settings.SECRET_KEY,
        "connect_timeout": 3,
        "max_reconnect_attempts": 2,
    }
    return opts


def make_random_password(*, len: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(len))


def days_until_cert_expires() -> int:
    cert_file, _ = get_certs()
    cert_bytes = Path(cert_file).read_bytes()

    cert = x509.load_pem_x509_certificate(cert_bytes)
    expires = cert.not_valid_after.replace(tzinfo=ZoneInfo("UTC"))
    delta = expires - djangotime.now()

    return delta.days
