from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import pytz
import random
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


def date_is_in_past(*, datetime_obj: "datetime", agent_tz: str) -> bool:
    """
    datetime_obj must be a naive datetime
    """
    now = djangotime.now()
    # convert agent tz to UTC to compare
    agent_pytz = pytz.timezone(agent_tz)
    localized = agent_pytz.localize(datetime_obj)
    utc_time = localized.astimezone(pytz.utc)
    return now > utc_time


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
    opts = {
        "servers": f"tls://{settings.ALLOWED_HOSTS[0]}:{nats_std_port}",
        "user": "tacticalrmm",
        "name": "trmm-django",
        "password": settings.SECRET_KEY,
        "connect_timeout": 3,
        "max_reconnect_attempts": 2,
    }
    return opts
