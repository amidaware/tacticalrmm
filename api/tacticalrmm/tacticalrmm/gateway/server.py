import asyncio
import logging
import os
import uuid

import asyncssh
from django.conf import settings

from .audit import _audit_session_failed
from .handlers import DirectSessionHandler, RejectionHandler
from .menu import MenuSessionHandler
from .permissions import (
    _fingerprint,
    _lookup_key,
    _resolve_and_check,
    _get_gateway_settings,
)
from .rate_limiter import _rate_limiter

logger = logging.getLogger("trmm")

_active_connections = 0
_active_connections_lock = asyncio.Lock()


def get_active_connections() -> int:
    return _active_connections


class GatewayServer(asyncssh.SSHServer):
    def __init__(self):
        self._auth_user = None
        self._auth_agent = None
        self._session_id = uuid.uuid4().hex
        self._conn = None
        self._remote_ip = ""
        self._client_version = ""
        self._ssh_key_name = ""
        self._ssh_key_type = ""
        self._ssh_key_fingerprint = ""
        self._is_menu = False
        self._conn_counted = False

    def connection_made(self, conn):
        self._conn = conn
        try:
            peer = conn.get_extra_info("peername", ("", 0))
            self._remote_ip = peer[0] if peer else ""
            self._client_version = conn.get_extra_info("client_version", "")
            logger.info(
                "Gateway connection from %s client=%s",
                self._remote_ip, self._client_version,
            )
        except Exception:
            self._remote_ip = ""
            self._client_version = ""
        global _active_connections
        _active_connections += 1
        self._conn_counted = True

    def connection_lost(self, exc):
        if self._conn_counted:
            self._conn_counted = False
            global _active_connections
            _active_connections -= 1
        if exc:
            logger.error("Gateway connection from %s lost: %s", self._remote_ip, exc)

    async def begin_auth(self, username):
        self._auth_user = None
        self._auth_agent = None
        self._is_menu = False
        self._session_id = uuid.uuid4().hex
        self._gateway_menu_enabled = True
        self._gateway_exec_enabled = True
        self._gateway_terminal_enabled = True
        self._gateway_session_timeout = 300
        self._gateway_max_sessions = 10
        if self._remote_ip and not _rate_limiter.allow(self._remote_ip):
            logger.warning("Gateway: rate limit exceeded for %s", self._remote_ip)
            return False
        try:
            core = await _get_gateway_settings()
            if core:
                self._gateway_menu_enabled = core.ssh_gateway_menu_enabled
                self._gateway_exec_enabled = core.ssh_gateway_exec_enabled
                self._gateway_terminal_enabled = core.ssh_gateway_terminal_enabled
                self._gateway_session_timeout = core.ssh_gateway_session_timeout
                self._gateway_max_sessions = core.ssh_gateway_max_sessions
        except Exception:
            logger.error("Gateway: failed to load settings", exc_info=True)
        return True

    def public_key_auth_supported(self):
        return True

    def password_auth_supported(self):
        return False

    def kbdint_auth_supported(self):
        return False

    async def validate_public_key(self, username, key):
        try:
            if hasattr(key, 'public_data'):
                raw = key.public_data
            else:
                raw = key.get_public_key_bytes()
            fp = _fingerprint(raw)

            ssh_key = await _lookup_key(fp)
            if ssh_key is None:
                logger.warning("Gateway: unknown key %s from %s", fp, self._remote_ip)
                asyncio.create_task(
                    _audit_session_failed(
                        username=username,
                        agent_id=username,
                        remote_ip=self._remote_ip,
                        reason="unknown_key",
                        ssh_key_fingerprint=fp,
                    )
                )
                return False

            user = ssh_key.user
            if not user.is_active or user.block_dashboard_login:
                logger.warning(
                    "Gateway: inactive user %s from %s", user.username, self._remote_ip
                )
                asyncio.create_task(
                    _audit_session_failed(
                        username=user.username,
                        agent_id=username,
                        remote_ip=self._remote_ip,
                        reason="inactive_user",
                        ssh_key_name=ssh_key.name,
                        ssh_key_type=ssh_key.key_type,
                        ssh_key_fingerprint=ssh_key.fingerprint,
                    )
                )
                return False

            self._ssh_key_name = ssh_key.name
            self._ssh_key_type = ssh_key.key_type
            self._ssh_key_fingerprint = ssh_key.fingerprint

            if username.lower() == "menu":
                from asgiref.sync import sync_to_async
                role = await sync_to_async(user.get_and_set_role_cache)()
                if not user.is_superuser and not (role and getattr(role, "can_use_terminal", False)):
                    logger.warning(
                        "Gateway: menu denied for user=%s from %s",
                        user.username, self._remote_ip,
                    )
                    asyncio.create_task(
                        _audit_session_failed(
                            username=user.username,
                            agent_id=username,
                            remote_ip=self._remote_ip,
                            reason="menu_no_permission",
                            ssh_key_name=ssh_key.name,
                            ssh_key_type=ssh_key.key_type,
                            ssh_key_fingerprint=ssh_key.fingerprint,
                        )
                    )
                    return False
                self._auth_user = user
                self._auth_agent = None
                self._is_menu = True
                logger.info(
                    "Gateway: menu session user=%s key=%s from %s",
                    user.username, ssh_key.name, self._remote_ip,
                )
                return True

            agent = await _resolve_and_check(user, username)
            if agent is None:
                logger.warning(
                    "Gateway: denied user=%s agent=%s from %s",
                    user.username, username, self._remote_ip,
                )
                asyncio.create_task(
                    _audit_session_failed(
                        username=user.username,
                        agent_id=username,
                        remote_ip=self._remote_ip,
                        reason="access_denied_no_permission",
                        ssh_key_name=ssh_key.name,
                        ssh_key_type=ssh_key.key_type,
                        ssh_key_fingerprint=ssh_key.fingerprint,
                    )
                )
                return False

            if agent.status != "online":
                logger.warning(
                    "Gateway: denied user=%s agent=%s from %s reason=agent_%s",
                    user.username, username, self._remote_ip, agent.status,
                )
                asyncio.create_task(
                    _audit_session_failed(
                        username=user.username,
                        agent_id=username,
                        remote_ip=self._remote_ip,
                        reason=f"agent_{agent.status}",
                        ssh_key_name=ssh_key.name,
                        ssh_key_type=ssh_key.key_type,
                        ssh_key_fingerprint=ssh_key.fingerprint,
                    )
                )
                return False

            self._auth_user = user
            self._auth_agent = agent
            logger.info(
                "Gateway: auth success user=%s agent=%s key=%s from %s",
                user.username, username, ssh_key.name, self._remote_ip,
            )
            return True
        except Exception as e:
            logger.error("Gateway: validate_public_key error: %s", e, exc_info=True)
            return False

    def session_requested(self):
        try:
            if self._is_menu:
                if not self._auth_user:
                    return None
                if not self._gateway_menu_enabled:
                    logger.warning("Gateway: menu denied (disabled) for %s", self._remote_ip)
                    audit = _audit_session_failed(
                        username=self._auth_user.username,
                        agent_id="menu",
                        remote_ip=self._remote_ip,
                        reason="menu_disabled",
                        ssh_key_name=self._ssh_key_name,
                        ssh_key_type=self._ssh_key_type,
                        ssh_key_fingerprint=self._ssh_key_fingerprint,
                    )
                    return RejectionHandler(
                        "SSH gateway menu access is disabled by your administrator.\r\n",
                        audit_coro=audit,
                    )
                return MenuSessionHandler(
                    self._auth_user, self._session_id, self._remote_ip,
                    client_version=self._client_version,
                    ssh_key_name=self._ssh_key_name,
                    ssh_key_type=self._ssh_key_type,
                    ssh_key_fingerprint=self._ssh_key_fingerprint,
                )
            if not self._auth_user or not self._auth_agent:
                return None
            return DirectSessionHandler(
                self._auth_user, self._auth_agent, self._session_id, self._remote_ip,
                client_version=self._client_version,
                ssh_key_name=self._ssh_key_name,
                ssh_key_type=self._ssh_key_type,
                ssh_key_fingerprint=self._ssh_key_fingerprint,
                gateway_exec_enabled=self._gateway_exec_enabled,
                gateway_terminal_enabled=self._gateway_terminal_enabled,
                gateway_session_timeout=self._gateway_session_timeout,
                gateway_max_sessions=self._gateway_max_sessions,
            )
        except Exception as e:
            logger.error("Gateway: session_requested error: %s", e, exc_info=True)
            return None


async def start_gateway(host=None, port=None):
    if host is None:
        host = getattr(settings, "SSH_SERVER_HOST", "0.0.0.0")
    if port is None:
        port = getattr(settings, "SSH_SERVER_PORT", 2222)

    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ValueError(f"Invalid gateway port: {port}")

    login_timeout = getattr(settings, "SSH_LOGIN_TIMEOUT", 30)
    if login_timeout < 5:
        logger.warning("SSH_LOGIN_TIMEOUT=%d too low, using 5", login_timeout)
        login_timeout = 5

    keepalive_interval = getattr(settings, "SSH_KEEPALIVE_INTERVAL", 30)
    keepalive_count_max = getattr(settings, "SSH_KEEPALIVE_COUNT_MAX", 3)
    if keepalive_interval < 5:
        logger.warning("SSH_KEEPALIVE_INTERVAL=%d too low, using 5", keepalive_interval)
        keepalive_interval = 5
    if keepalive_count_max < 1:
        logger.warning("SSH_KEEPALIVE_COUNT_MAX=%d too low, using 1", keepalive_count_max)
        keepalive_count_max = 1

    host_key_path = getattr(settings, "SSH_HOST_KEY", "/etc/trmm/ssh_host_key")
    if not os.path.exists(host_key_path):
        logger.warning("SSH host key not found at %s, generating...", host_key_path)
        os.makedirs(os.path.dirname(host_key_path), exist_ok=True)
        key = asyncssh.generate_private_key("ssh-rsa")
        key.write_private_key(host_key_path)

    server_host_keys = [host_key_path]

    server = await asyncssh.create_server(
        GatewayServer,
        host,
        port,
        server_host_keys=server_host_keys,
        public_key_auth=True,
        password_auth=False,
        kbdint_auth=False,
        kex_algs=["mlkem768x25519-sha256", "curve25519-sha256"],
        line_editor=False,
        login_timeout=login_timeout,
        keepalive_interval=keepalive_interval,
        keepalive_count_max=keepalive_count_max,
        reuse_address=True,
    )
    logger.info(
        "Gateway listening on %s:%s (timeout=%d keepalive=%d/%d)",
        host, port, login_timeout, keepalive_interval, keepalive_count_max,
    )
    return server