from __future__ import annotations

import os
import random
import secrets
import string
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from zoneinfo import ZoneInfo

from cryptography import x509
from django.conf import settings
from django.utils import timezone as djangotime
from rest_framework import status
from rest_framework.response import Response

if TYPE_CHECKING:
    from datetime import datetime

    from alerts.models import AlertTemplate


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
    if getattr(settings, "USE_NATS_STANDARD", False):
        return "tls"

    return "nats"


def get_nats_hosts() -> tuple[str, str, str]:
    std_bind_host = "0.0.0.0"
    ws_bind_host = "0.0.0.0"
    connect_host = settings.ALLOWED_HOSTS[0]

    # standard install
    if not settings.DOCKER_BUILD and not getattr(settings, "USE_NATS_STANDARD", False):
        std_bind_host, ws_bind_host, connect_host = (
            "127.0.0.1",
            "127.0.0.1",
            "127.0.0.1",
        )

    # allow customizing all nats hosts
    if "NATS_STD_BIND_HOST" in os.environ:
        std_bind_host = os.getenv("NATS_STD_BIND_HOST")
    elif hasattr(settings, "NATS_STD_BIND_HOST"):
        std_bind_host = settings.NATS_STD_BIND_HOST

    if "NATS_WS_BIND_HOST" in os.environ:
        ws_bind_host = os.getenv("NATS_WS_BIND_HOST")
    elif hasattr(settings, "NATS_WS_BIND_HOST"):
        ws_bind_host = settings.NATS_WS_BIND_HOST

    if "NATS_CONNECT_HOST" in os.environ:
        connect_host = os.getenv("NATS_CONNECT_HOST")
    elif hasattr(settings, "NATS_CONNECT_HOST"):
        connect_host = settings.NATS_CONNECT_HOST

    return std_bind_host, ws_bind_host, connect_host


def get_nats_url() -> str:
    _, _, connect_host = get_nats_hosts()
    proto = get_nats_internal_protocol()
    port, _ = get_nats_ports()
    return f"{proto}://{connect_host}:{port}"


def date_is_in_past(*, datetime_obj: "datetime", agent_tz: str) -> bool:
    """
    datetime_obj must be a naive datetime
    """
    # convert agent tz to UTC to compare
    localized = datetime_obj.replace(tzinfo=ZoneInfo(agent_tz))
    utc_time = localized.astimezone(ZoneInfo("UTC"))
    return djangotime.now() > utc_time


def rand_range(min: int, max: int) -> float:
    """
    Input is milliseconds.
    Returns float truncated to 2 decimals.
    """
    return round(random.uniform(min, max) / 1000, 2)


def setup_nats_options() -> dict[str, Any]:
    opts = {
        "servers": get_nats_url(),
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
    delta = cert.not_valid_after_utc - djangotime.now()

    return delta.days


def has_webhook(
    alert_templ: AlertTemplate | None, instance: Literal["agent", "check", "task"]
) -> bool:
    return bool(
        alert_templ
        and (alert_templ.action_rest or alert_templ.resolved_action_rest)
        and (
            (instance == "agent" and alert_templ.agent_script_actions)
            or (instance == "check" and alert_templ.check_script_actions)
            or (instance == "task" and alert_templ.task_script_actions)
        )
    )


def has_script_actions(
    alert_templ: AlertTemplate | None, instance: Literal["agent", "check", "task"]
) -> bool:
    return bool(
        alert_templ
        and (alert_templ.action or alert_templ.resolved_action)
        and (
            (instance == "agent" and alert_templ.agent_script_actions)
            or (instance == "check" and alert_templ.check_script_actions)
            or (instance == "task" and alert_templ.task_script_actions)
        )
    )
