import asyncio
import os
import uuid

import asyncssh
from django.conf import settings

from .audit import _audit_session_failed
from .functions import FUNCTION_REGISTRY
from .handlers import DirectSessionHandler, RejectionHandler
from .logger import gw_log
from .permissions import (
    _fingerprint,
    _lookup_key,
    _resolve_and_check,
    _get_gateway_settings,
)
from .rate_limiter import _rate_limiter

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
            gw_log.info(
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
            gw_log.error("Gateway connection from %s lost: %s", self._remote_ip, exc)

    async def begin_auth(self, username):
        self._auth_user = None
        self._auth_agent = None
        self._is_menu = False
        self._is_function = False
        self._function_handler_cls = None
        self._session_id = uuid.uuid4().hex
        self._gateway_menu_enabled = True
        self._gateway_exec_enabled = True
        self._gateway_terminal_enabled = True
        self._gateway_session_timeout = 300
        self._gateway_max_sessions = 10
        self._gateway_rate_limit_max_entries = 10
        try:
            core = await _get_gateway_settings()
            if core:
                self._gateway_menu_enabled = core.ssh_gateway_menu_enabled
                self._gateway_exec_enabled = core.ssh_gateway_exec_enabled
                self._gateway_terminal_enabled = core.ssh_gateway_terminal_enabled
                self._gateway_session_timeout = core.ssh_gateway_session_timeout
                self._gateway_max_sessions = core.ssh_gateway_max_sessions
                self._gateway_rate_limit_max_entries = core.ssh_gateway_rate_limit_max_entries
                _rate_limiter.configure(max_attempts=core.ssh_gateway_rate_limit_max_entries)
        except Exception:
            gw_log.error("Gateway: failed to load settings", exc_info=True)
        if self._remote_ip and not _rate_limiter.allow(self._remote_ip):
            gw_log.warning("Gateway: rate limit exceeded for %s", self._remote_ip)
            return False
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
            elif hasattr(key, 'get_public_key_bytes'):
                raw = key.get_public_key_bytes()
            else:
                raw = key.public_bytes(raw=True) if hasattr(key, 'public_bytes') else None
            if raw is None:
                return False
            fp = _fingerprint(raw)

            ssh_key = await _lookup_key(fp)
            if ssh_key is None:
                gw_log.warning("Gateway: unknown key %s from %s", fp, self._remote_ip)
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
                gw_log.warning(
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
                if not user.is_superuser and not (role and getattr(role, "can_ssh_use_functions", False)):
                    gw_log.warning(
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
                gw_log.info(
                    "Gateway: menu session user=%s key=%s from %s",
                    user.username, ssh_key.name, self._remote_ip,
                )
                return True

            func_username = username.lower()
            if func_username in FUNCTION_REGISTRY:
                from asgiref.sync import sync_to_async
                role = await sync_to_async(user.get_and_set_role_cache)()
                can_use = getattr(role, "can_ssh_use_functions", False) if role else False
                if not user.is_superuser and not can_use:
                    gw_log.warning(
                        "Gateway: function %s denied for user=%s from %s",
                        func_username, user.username, self._remote_ip,
                    )
                    asyncio.create_task(
                        _audit_session_failed(
                            username=user.username,
                            agent_id=username,
                            remote_ip=self._remote_ip,
                            reason="function_no_permission",
                            ssh_key_name=ssh_key.name,
                            ssh_key_type=ssh_key.key_type,
                            ssh_key_fingerprint=ssh_key.fingerprint,
                        )
                    )
                    return False
                self._auth_user = user
                self._auth_agent = None
                self._is_function = True
                self._function_handler_cls = FUNCTION_REGISTRY[func_username]
                gw_log.info(
                    "Gateway: function %s session user=%s key=%s from %s",
                    func_username, user.username, ssh_key.name, self._remote_ip,
                )
                return True

            agent = await _resolve_and_check(user, username)
            if agent is None:
                gw_log.warning(
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
                gw_log.warning(
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
            gw_log.info(
                "Gateway: auth success user=%s agent=%s key=%s from %s",
                user.username, username, ssh_key.name, self._remote_ip,
            )
            return True
        except Exception as e:
            gw_log.error("Gateway: validate_public_key error: %s", e, exc_info=True)
            return False

    def session_requested(self):
        try:
            if self._is_menu:
                if not self._auth_user:
                    return None
                if not self._gateway_menu_enabled:
                    gw_log.warning("Gateway: menu denied (disabled) for %s", self._remote_ip)
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
                return FUNCTION_REGISTRY["menu"](
                    self._auth_user, self._session_id, self._remote_ip,
                    client_version=self._client_version,
                    ssh_key_name=self._ssh_key_name,
                    ssh_key_type=self._ssh_key_type,
                    ssh_key_fingerprint=self._ssh_key_fingerprint,
                )
            if self._is_function:
                if not self._auth_user or not self._function_handler_cls:
                    return None
                return self._function_handler_cls(
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
            gw_log.error("Gateway: session_requested error: %s", e, exc_info=True)
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
        gw_log.warning("SSH_LOGIN_TIMEOUT=%d too low, using 5", login_timeout)
        login_timeout = 5

    keepalive_interval = getattr(settings, "SSH_KEEPALIVE_INTERVAL", 30)
    keepalive_count_max = getattr(settings, "SSH_KEEPALIVE_COUNT_MAX", 3)
    if keepalive_interval < 5:
        gw_log.warning("SSH_KEEPALIVE_INTERVAL=%d too low, using 5", keepalive_interval)
        keepalive_interval = 5
    if keepalive_count_max < 1:
        gw_log.warning("SSH_KEEPALIVE_COUNT_MAX=%d too low, using 1", keepalive_count_max)
        keepalive_count_max = 1

    host_key_path = getattr(settings, "SSH_HOST_KEY", "/etc/trmm/ssh_host_key")
    if not os.path.exists(host_key_path):
        gw_log.warning("SSH host key not found at %s, generating...", host_key_path)
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
    gw_log.info(
        "Gateway listening on %s:%s (timeout=%d keepalive=%d/%d)",
        host, port, login_timeout, keepalive_interval, keepalive_count_max,
    )
    return server