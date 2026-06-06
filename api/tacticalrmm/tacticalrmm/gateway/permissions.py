import asyncio
import logging
from hashlib import sha256
import base64

from asgiref.sync import sync_to_async

from .audit import _audit_session_failed

logger = logging.getLogger("trmm")


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


def _validate_key(key) -> tuple[bytes, str]:
    if hasattr(key, 'public_data'):
        raw = key.public_data
    else:
        raw = key.get_public_key_bytes()
    fp = _fingerprint(raw)
    return raw, fp


async def validate_ssh_key(fp: str) -> tuple[bool, str, dict]:
    ssh_key = await _lookup_key(fp)
    if ssh_key is None:
        logger.warning("Gateway: unknown key %s", fp)
        asyncio.create_task(_audit_session_failed(
            username="unknown",
            agent_id="unknown",
            remote_ip="unknown",
            reason="unknown_key",
            ssh_key_fingerprint=fp,
        ))
        return False, "unknown_key", {}

    user = ssh_key.user
    return True, "", {
        "ssh_key": ssh_key,
        "user": user,
        "ssh_key_name": ssh_key.name,
        "ssh_key_type": ssh_key.key_type,
        "ssh_key_fingerprint": ssh_key.fingerprint,
    }


async def validate_user_active(user) -> tuple[bool, str, dict]:
    if not user.is_active or user.block_dashboard_login:
        logger.warning("Gateway: inactive user %s", user.username)
        asyncio.create_task(_audit_session_failed(
            username=user.username,
            agent_id="unknown",
            remote_ip="unknown",
            reason="inactive_user",
            ssh_key_name=getattr(user, 'ssh_key_name', ''),
            ssh_key_type=getattr(user, 'ssh_key_type', ''),
            ssh_key_fingerprint=getattr(user, 'ssh_key_fingerprint', ''),
        ))
        return False, "inactive_user", {}

    return True, "", {}


async def validate_menu_access(user) -> tuple[bool, str, dict]:
    role = await sync_to_async(user.get_and_set_role_cache)()
    if not user.is_superuser and not (role and getattr(role, "can_use_terminal", False)):
        logger.warning("Gateway: menu denied for user=%s", user.username)
        asyncio.create_task(_audit_session_failed(
            username=user.username,
            agent_id="menu",
            remote_ip="unknown",
            reason="menu_no_permission",
        ))
        return False, "menu_no_permission", {}

    return True, "", {"role": role}


async def validate_agent_access(user, agent_id: str) -> tuple[bool, str, dict]:
    agent = await _resolve_and_check(user, agent_id)
    if agent is None:
        logger.warning("Gateway: denied user=%s agent=%s", user.username, agent_id)
        asyncio.create_task(_audit_session_failed(
            username=user.username,
            agent_id=agent_id,
            remote_ip="unknown",
            reason="access_denied_no_permission",
        ))
        return False, "access_denied_no_permission", {}

    if agent.status != "online":
        logger.warning("Gateway: denied user=%s agent=%s reason=agent_%s",
                       user.username, agent_id, agent.status)
        asyncio.create_task(_audit_session_failed(
            username=user.username,
            agent_id=agent_id,
            remote_ip="unknown",
            reason=f"agent_{agent.status}",
        ))
        return False, f"agent_{agent.status}", {}

    return True, "", {"agent": agent}


async def get_key_and_user(fp: str):
    ssh_key = await _lookup_key(fp)
    if ssh_key is None:
        return None, None
    return ssh_key, ssh_key.user


async def check_user_can_access_agent(user, agent_id: str) -> bool:
    agent = await _resolve_and_check(user, agent_id)
    return agent is not None


async def check_user_can_use_menu(user) -> bool:
    if user.is_superuser:
        return True
    role = await sync_to_async(user.get_and_set_role_cache)()
    return role and getattr(role, "can_use_terminal", False)


async def check_agent_online(agent) -> bool:
    return agent.status == "online"