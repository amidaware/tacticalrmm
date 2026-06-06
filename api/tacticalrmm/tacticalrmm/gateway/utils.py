import asyncio
import logging
from hashlib import sha256
import base64

from asgiref.sync import sync_to_async

logger = logging.getLogger("trmm")


def _safe_task(coro, name=""):
    task = asyncio.create_task(coro)

    def _log_exception(fut):
        exc = fut.exception()
        if exc:
            logger.error("SSH task '%s' failed: %s", name, exc, exc_info=True)

    task.add_done_callback(_log_exception)
    return task


def _fingerprint(key_bytes: bytes) -> str:
    digest = sha256(key_bytes).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


@sync_to_async
def _lookup_key(fp: str):
    from accounts.models import SSHPublicKey
    try:
        return SSHPublicKey.objects.select_related("user__role").get(fingerprint=fp)
    except SSHPublicKey.DoesNotExist:
        return None


@sync_to_async
def _resolve_and_check(user, agent_id: str):
    from agents.models import Agent
    if user.is_superuser:
        try:
            return Agent.objects.get(agent_id=agent_id)
        except Agent.DoesNotExist:
            return None
    role = user.get_and_set_role_cache()
    if role and getattr(role, "is_superuser", False):
        try:
            return Agent.objects.get(agent_id=agent_id)
        except Agent.DoesNotExist:
            return None
    if not role:
        return None
    if not getattr(role, "can_use_terminal", False):
        return None
    try:
        agent = Agent.objects.defer("wmi_detail", "services").select_related(
            "site__client"
        ).get(agent_id=agent_id)
    except Agent.DoesNotExist:
        return None
    can_view_clients = role.can_view_clients.all() if role else None
    can_view_sites = role.can_view_sites.all() if role else None
    if not can_view_clients and not can_view_sites:
        return agent
    if can_view_clients and agent.client in can_view_clients:
        return agent
    if can_view_sites and agent.site in can_view_sites:
        return agent
    return None


@sync_to_async
def _get_user_group(user):
    return user.role.name if user.role else None


@sync_to_async
def _get_gateway_settings():
    from core.models import CoreSettings
    return CoreSettings.objects.first()
