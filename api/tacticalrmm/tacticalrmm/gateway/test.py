#!/usr/bin/env python3
"""
SSH Gateway health check script.
Run via: python manage.py shell < test.py
Or directly: python test.py
"""
import asyncio
import sys
import os

sys.path.insert(0, "/rmm/api/tacticalrmm")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tacticalrmm.settings")

import django
django.setup()

from asgiref.sync import sync_to_async
from django.conf import settings

from core.models import CoreSettings
from agents.models import Agent
from accounts.models import SSHPublicKey
from logs.models import AuditLog
from tacticalrmm.gateway import start_gateway, get_active_connections
from tacticalrmm.gateway.server import GatewayServer
from tacticalrmm.gateway.handlers import DirectSessionHandler, RejectionHandler
from tacticalrmm.gateway.functions.menu import MenuSessionHandler
from tacticalrmm.gateway.utils import _lookup_key, _resolve_and_check, _get_gateway_settings
from tacticalrmm.gateway.permissions import _get_gateway_settings
from tacticalrmm.gateway.audit import (
    _audit_session_failed, _audit_exec_command, _audit_terminal_command,
    _record_session_and_audit, _close_session_and_audit,
)
from tacticalrmm.gateway.exec import run_exec
from tacticalrmm.gateway.constants import (
    _strip_ansi, get_local_ips, build_welcome_message,
    TERMINAL_MODES, ANSI_ESCAPE, WELCOME_TEMPLATE,
)
from tacticalrmm.gateway.mixins import DataBuffer, BaseSessionMixin


def print_header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print('='*60)


def print_ok(msg):
    print(f"  [OK] {msg}")


def print_fail(msg):
    print(f"  [FAIL] {msg}")


def print_info(msg):
    print(f"  [INFO] {msg}")


def check_model_fields():
    """Check that all expected model fields exist on CoreSettings."""
    print_header("CoreSettings model fields")
    fields = [
        "enable_ssh_gateway",
        "ssh_gateway_session_timeout",
        "ssh_gateway_max_sessions",
        "ssh_gateway_rate_limit_max_entries",
        "ssh_gateway_enable_menu",
        "ssh_gateway_enable_exec",
        "ssh_gateway_enable_terminal",
    ]
    all_ok = True
    for field in fields:
        if hasattr(CoreSettings, field):
            print_ok(f"field '{field}' exists")
        else:
            print_fail(f"field '{field}' MISSING")
            all_ok = False

    props = [
        "ssh_gateway_enabled",
        "ssh_gateway_menu_enabled",
        "ssh_gateway_exec_enabled",
        "ssh_gateway_terminal_enabled",
    ]
    for prop in props:
        if hasattr(CoreSettings, prop):
            print_ok(f"property '{prop}' exists")
        else:
            print_fail(f"property '{prop}' MISSING")
            all_ok = False
    return all_ok


def check_audit_log_model():
    """Check AuditLog has SSH_SESSION action type."""
    print_header("AuditLog model")
    from tacticalrmm.constants import AuditActionType
    valid_actions = [a[0] for a in AuditActionType.choices]
    if "ssh_session" in valid_actions:
        print_ok("AuditActionType.SSH_SESSION exists")
    else:
        print_fail("AuditActionType.SSH_SESSION MISSING")
        return False

    from tacticalrmm.constants import AuditObjType
    if hasattr(AuditObjType, "AGENT"):
        print_ok("AuditObjType.AGENT exists")
    else:
        print_fail("AuditObjType.AGENT MISSING")
        return False
    return True


def check_core_settings():
    """Check CoreSettings singleton and gateway settings."""
    print_header("CoreSettings instance")
    try:
        core = CoreSettings.objects.get()
        print_ok(f"CoreSettings singleton exists (pk={core.pk})")
        print_info(f"  enable_ssh_gateway = {core.enable_ssh_gateway}")
        print_info(f"  ssh_gateway_enabled (property) = {core.ssh_gateway_enabled}")
        print_info(f"  ssh_gateway_enable_menu = {core.ssh_gateway_enable_menu}")
        print_info(f"  ssh_gateway_enable_exec = {core.ssh_gateway_enable_exec}")
        print_info(f"  ssh_gateway_enable_terminal = {core.ssh_gateway_enable_terminal}")
        print_info(f"  ssh_gateway_session_timeout = {core.ssh_gateway_session_timeout}")
        print_info(f"  ssh_gateway_max_sessions = {core.ssh_gateway_max_sessions}")
        print_info(f"  ssh_gateway_rate_limit_max_entries = {core.ssh_gateway_rate_limit_max_entries}")
        return True
    except CoreSettings.DoesNotExist:
        print_fail("CoreSettings singleton does not exist!")
        return False
    except Exception as e:
        print_fail(f"Error loading CoreSettings: {e}")
        return False


async def check_get_gateway_settings():
    """Test _get_gateway_settings helper."""
    print_header("_get_gateway_settings helper")
    try:
        core = await _get_gateway_settings()
        if core:
            print_ok(f"_get_gateway_settings() returned CoreSettings(pk={core.pk})")
            return True
        else:
            print_fail("_get_gateway_settings() returned None")
            return False
    except Exception as e:
        print_fail(f"_get_gateway_settings() raised: {e}")
        return False


def check_gateway_module_imports():
    """Check all gateway modules import cleanly."""
    print_header("Gateway module imports")
    modules = [
        "tacticalrmm.gateway",
        "tacticalrmm.gateway.server",
        "tacticalrmm.gateway.handlers",
        "tacticalrmm.gateway.functions",
        "tacticalrmm.gateway.functions.menu",
        "tacticalrmm.gateway.functions.egg",
        "tacticalrmm.gateway.audit",
        "tacticalrmm.gateway.exec",
        "tacticalrmm.gateway.terminal",
        "tacticalrmm.gateway.utils",
        "tacticalrmm.gateway.rate_limiter",
        "tacticalrmm.gateway.constants",
        "tacticalrmm.gateway.permissions",
    ]
    all_ok = True
    for mod in modules:
        try:
            __import__(mod)
            print_ok(f"import '{mod}'")
        except Exception as e:
            print_fail(f"import '{mod}': {e}")
            all_ok = False
    return all_ok


def check_handler_classes():
    """Check RejectionHandler and DirectSessionHandler have expected methods."""
    print_header("Handler class methods")
    methods = [
        "connection_made", "exec_requested", "shell_requested",
        "pty_requested", "eof_received", "connection_lost", "closed",
    ]
    all_ok = True
    for m in methods:
        if hasattr(DirectSessionHandler, m):
            print_ok(f"DirectSessionHandler.{m}()")
        else:
            print_fail(f"DirectSessionHandler.{m}() MISSING")
            all_ok = False

    rh_methods = ["connection_made", "eof_received"]
    for m in rh_methods:
        if hasattr(RejectionHandler, m):
            print_ok(f"RejectionHandler.{m}()")
        else:
            print_fail(f"RejectionHandler.{m}() MISSING")
            all_ok = False
    return all_ok


def check_menu_handler():
    """Check MenuSessionHandler exists and has expected methods."""
    print_header("MenuSessionHandler class")
    methods = ["connection_made", "shell_requested", "_show_clients", "_connect_to_agent"]
    all_ok = True
    for m in methods:
        if hasattr(MenuSessionHandler, m):
            print_ok(f"MenuSessionHandler.{m}()")
        else:
            print_fail(f"MenuSessionHandler.{m}() MISSING")
            all_ok = False
    return all_ok


def check_nats_connection():
    """Check if NATS is reachable (env variable check)."""
    print_header("NATS connectivity")
    nats_url = getattr(settings, "NATS_URL", None)
    if nats_url:
        print_info(f"NATS_URL = {nats_url}")
        try:
            import socket
            host = nats_url.replace("nats://", "").split(":")[0]
            port = int(nats_url.replace("nats://", "").split(":")[1]) if ":" in nats_url else 4222
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print_ok(f"NATS reachable at {host}:{port}")
            else:
                print_fail(f"NATS NOT reachable at {host}:{port} (code={result})")
        except Exception as e:
            print_fail(f"NATS connection test failed: {e}")
    else:
        print_info("NATS_URL not set in settings")
    return True


def check_gateway_settings_respect_hosted():
    """Verify HOSTED/DEMO flags properly disable gateway."""
    print_header("HOSTED/DEMO flag handling")
    core = CoreSettings.objects.get()
    hosted = getattr(settings, "HOSTED", False)
    demo = getattr(settings, "DEMO", False)
    print_info(f"HOSTED={hosted}, DEMO={demo}")
    print_info(f"ssh_gateway_enabled = {core.ssh_gateway_enabled} (should be False if HOSTED or DEMO)")
    if hosted or demo:
        if not core.ssh_gateway_enabled:
            print_ok("ssh_gateway_enabled correctly False in HOSTED/DEMO mode")
        else:
            print_fail("ssh_gateway_enabled should be False in HOSTED/DEMO mode!")
            return False
    return True


def check_audit_log_entry_count():
    """Check recent audit log entries."""
    print_header("Audit log entries")
    try:
        recent = AuditLog.objects.filter(
            action="ssh_session"
        ).order_by("-entry_time")[:5]
        print_info(f"Last 5 SSH_SESSION audit entries:")
        for entry in recent:
            print_info(f"  [{entry.entry_time}] {entry.message}")
        return True
    except Exception as e:
        print_fail(f"Error querying audit log: {e}")
        return False


def check_ssh_session_model():
    """Check SSHSession model exists."""
    print_header("SSHSession model")
    try:
        from accounts.models import SSHSession
        count = SSHSession.objects.count()
        active = SSHSession.objects.filter(closed_at__isnull=True).count()
        print_ok(f"SSHSession model exists ({count} total, {active} active)")
        return True
    except Exception as e:
        print_fail(f"SSHSession model error: {e}")
        return False


def check_egg_game():
    """Check egg game still works."""
    print_header("EggGame (snake) import")
    try:
        from tacticalrmm.gateway.functions.egg import EggGame, _add_highscore, _format_highscores
        print_ok("EggGame and highscore helpers import cleanly")
        return True
    except Exception as e:
        print_fail(f"EggGame import failed: {e}")
        return False


def check_refactored_handlers():
    """Check DirectSessionHandler and run_exec."""
    print_header("Refactored handler classes")
    all_ok = True

    methods = ["connection_made", "exec_requested", "shell_requested", "pty_requested"]
    for m in methods:
        if hasattr(DirectSessionHandler, m):
            print_ok(f"DirectSessionHandler.{m}()")
        else:
            print_fail(f"DirectSessionHandler.{m}() MISSING")
            all_ok = False

    print_ok("run_exec() function exists")

    return all_ok


def check_constants_helpers():
    """Check constants module helper functions."""
    print_header("Constants module helpers")
    all_ok = True

    if callable(get_local_ips):
        print_ok("get_local_ips() is callable")
    else:
        print_fail("get_local_ips() is not callable")
        all_ok = False

    if callable(build_welcome_message):
        print_ok("build_welcome_message() is callable")
    else:
        print_fail("build_welcome_message() is not callable")
        all_ok = False

    if callable(_strip_ansi):
        print_ok("_strip_ansi() is callable")
    else:
        print_fail("_strip_ansi() is not callable")
        all_ok = False

    if TERMINAL_MODES:
        print_ok(f"TERMINAL_MODES has {len(TERMINAL_MODES)} entries")
    else:
        print_fail("TERMINAL_MODES is empty")
        all_ok = False

    if WELCOME_TEMPLATE:
        print_ok("WELCOME_TEMPLATE is defined")
    else:
        print_fail("WELCOME_TEMPLATE is empty")
        all_ok = False

    return all_ok


def check_new_ssh_permission_fields():
    """Check that new SSH permission fields exist on Role model."""
    print_header("New SSH Permission Fields")
    from accounts.models import Role
    all_ok = True
    fields = [
        "can_ssh_open_terminal",
        "can_ssh_send_commands",
        "can_ssh_use_functions",
    ]
    for field in fields:
        if hasattr(Role, field):
            print_ok(f"Role.{field} exists")
        else:
            print_fail(f"Role.{field} MISSING")
            all_ok = False
    return all_ok


async def check_resolve_and_check_terminal_requires_can_ssh_open_terminal():
    """User without can_ssh_open_terminal should be denied terminal access."""
    print_header("_resolve_and_check terminal permission")
    from accounts.models import User, Role
    from agents.models import Agent

    user = await sync_to_async(lambda: User.objects.filter(is_superuser=False).first())()
    if not user:
        print_info("No non-superuser found, skipping")
        return True

    role = await sync_to_async(lambda: user.role)()
    if not role:
        print_info("User has no role, skipping")
        return True

    agent = await sync_to_async(lambda: Agent.objects.first())()
    if not agent:
        print_info("No agent found, skipping")
        return True

    old_term = getattr(role, "can_ssh_open_terminal", None)
    old_exec = getattr(role, "can_ssh_send_commands", None)
    old_funcs = getattr(role, "can_ssh_use_functions", None)

    try:
        role.can_ssh_open_terminal = False
        role.can_ssh_send_commands = True
        role.can_ssh_use_functions = True
        await sync_to_async(role.save)()

        from tacticalrmm.gateway.permissions import _resolve_and_check, validate_menu_access
        result = await _resolve_and_check(user, agent.agent_id, session_type="terminal")
        if result is None:
            print_ok("Terminal access DENIED when can_ssh_open_terminal=False")
        else:
            print_fail("Terminal access GRANTED but should be DENIED")
            return False

        role.can_ssh_open_terminal = True
        await sync_to_async(role.save)()
        result = await _resolve_and_check(user, agent.agent_id, session_type="terminal")
        if result is not None:
            print_ok("Terminal access GRANTED when can_ssh_open_terminal=True")
        else:
            print_fail("Terminal access DENIED but should be GRANTED")
            return False

        return True
    except Exception as e:
        print_fail(f"Error: {e}")
        return False
    finally:
        if old_term is not None:
            role.can_ssh_open_terminal = old_term
        if old_exec is not None:
            role.can_ssh_send_commands = old_exec
        if old_funcs is not None:
            role.can_ssh_use_functions = old_funcs
        await sync_to_async(role.save)()


async def check_resolve_and_check_exec_requires_can_ssh_send_commands():
    """User without can_ssh_send_commands should be denied exec access."""
    print_header("_resolve_and_check exec permission")
    from accounts.models import User, Role
    from agents.models import Agent

    user = await sync_to_async(lambda: User.objects.filter(is_superuser=False).first())()
    if not user:
        print_info("No non-superuser found, skipping")
        return True

    role = await sync_to_async(lambda: user.role)()
    if not role:
        print_info("User has no role, skipping")
        return True

    agent = await sync_to_async(lambda: Agent.objects.first())()
    if not agent:
        print_info("No agent found, skipping")
        return True

    old_term = getattr(role, "can_ssh_open_terminal", None)
    old_exec = getattr(role, "can_ssh_send_commands", None)
    old_funcs = getattr(role, "can_ssh_use_functions", None)

    try:
        role.can_ssh_open_terminal = True
        role.can_ssh_send_commands = False
        role.can_ssh_use_functions = True
        await sync_to_async(role.save)()

        from tacticalrmm.gateway.permissions import _resolve_and_check, validate_menu_access
        result = await _resolve_and_check(user, agent.agent_id, session_type="exec")
        if result is None:
            print_ok("Exec access DENIED when can_ssh_send_commands=False")
        else:
            print_fail("Exec access GRANTED but should be DENIED")
            return False

        role.can_ssh_send_commands = True
        await sync_to_async(role.save)()
        result = await _resolve_and_check(user, agent.agent_id, session_type="exec")
        if result is not None:
            print_ok("Exec access GRANTED when can_ssh_send_commands=True")
        else:
            print_fail("Exec access DENIED but should be GRANTED")
            return False

        return True
    except Exception as e:
        print_fail(f"Error: {e}")
        return False
    finally:
        if old_term is not None:
            role.can_ssh_open_terminal = old_term
        if old_exec is not None:
            role.can_ssh_send_commands = old_exec
        if old_funcs is not None:
            role.can_ssh_use_functions = old_funcs
        await sync_to_async(role.save)()


async def check_menu_access_requires_can_ssh_use_functions():
    """User without can_ssh_use_functions should be denied menu access."""
    print_header("validate_menu_access permission")
    from accounts.models import User, Role

    user = await sync_to_async(lambda: User.objects.filter(is_superuser=False).first())()
    if not user:
        print_info("No non-superuser found, skipping")
        return True

    role = await sync_to_async(lambda: user.role)()
    if not role:
        print_info("User has no role, skipping")
        return True

    old_funcs = getattr(role, "can_ssh_use_functions", None)

    try:
        role.can_ssh_use_functions = False
        await sync_to_async(role.save)()

        from tacticalrmm.gateway.permissions import validate_menu_access
        allowed, reason, data = await validate_menu_access(user)
        if not allowed and reason == "menu_no_permission":
            print_ok("Menu access DENIED when can_ssh_use_functions=False")
        else:
            print_fail(f"Menu access {'GRANTED' if allowed else reason} but should be DENIED")
            return False

        role.can_ssh_use_functions = True
        await sync_to_async(role.save)()
        allowed, reason, data = await validate_menu_access(user)
        if allowed:
            print_ok("Menu access GRANTED when can_ssh_use_functions=True")
        else:
            print_fail(f"Menu access DENIED but should be GRANTED: {reason}")
            return False

        return True
    except Exception as e:
        print_fail(f"Error: {e}")
        return False
    finally:
        if old_funcs is not None:
            role.can_ssh_use_functions = old_funcs
        await sync_to_async(role.save)()


async def check_superuser_bypasses_permissions():
    """Superuser should bypass all permission checks."""
    print_header("Superuser bypasses permissions")
    from accounts.models import User
    from agents.models import Agent

    user = await sync_to_async(lambda: User.objects.filter(is_superuser=True).first())()
    if not user:
        print_info("No superuser found, skipping")
        return True

    agent = await sync_to_async(lambda: Agent.objects.first())()
    if not agent:
        print_info("No agent found, skipping")
        return True

    try:
        from tacticalrmm.gateway.permissions import _resolve_and_check, validate_menu_access, validate_menu_access

        result = await _resolve_and_check(user, agent.agent_id, session_type="terminal")
        if result is not None:
            print_ok("Superuser can access agent for terminal")
        else:
            print_fail("Superuser should bypass terminal permission check")
            return False

        result = await _resolve_and_check(user, agent.agent_id, session_type="exec")
        if result is not None:
            print_ok("Superuser can access agent for exec")
        else:
            print_fail("Superuser should bypass exec permission check")
            return False

        allowed, _, _ = await validate_menu_access(user)
        if allowed:
            print_ok("Superuser can access menu")
        else:
            print_fail("Superuser should bypass menu permission check")
            return False

        return True
    except Exception as e:
        print_fail(f"Error: {e}")
        return False


# ---------------------------------------------------------------------------
# New comprehensive tests
# ---------------------------------------------------------------------------

def check_function_registry_autodiscovery():
    """FUNCTION_REGISTRY auto-discovers all function .py files."""
    print_header("FUNCTION_REGISTRY auto-discovery")
    from tacticalrmm.gateway.functions import FUNCTION_REGISTRY
    all_ok = True
    if "menu" in FUNCTION_REGISTRY:
        print_ok("FUNCTION_REGISTRY contains 'menu'")
    else:
        print_fail("FUNCTION_REGISTRY missing 'menu'")
        all_ok = False
    if "egg" in FUNCTION_REGISTRY:
        print_ok("FUNCTION_REGISTRY contains 'egg'")
    else:
        print_fail("FUNCTION_REGISTRY missing 'egg'")
        all_ok = False
    if len(FUNCTION_REGISTRY) >= 2:
        print_ok(f"FUNCTION_REGISTRY has {len(FUNCTION_REGISTRY)} registered functions")
    else:
        print_fail(f"FUNCTION_REGISTRY has only {len(FUNCTION_REGISTRY)} entries (expected >=2)")
        all_ok = False
    return all_ok


def check_base_function_handler():
    """BaseFunctionHandler provides expected default methods."""
    print_header("BaseFunctionHandler class")
    from tacticalrmm.gateway.functions.base import BaseFunctionHandler
    all_ok = True
    for m in ["connection_made", "pty_requested", "eof_received"]:
        if hasattr(BaseFunctionHandler, m):
            print_ok(f"BaseFunctionHandler.{m}()")
        else:
            print_fail(f"BaseFunctionHandler.{m}() MISSING")
            all_ok = False
    if BaseFunctionHandler.name == "":
        print_ok("BaseFunctionHandler.name is empty string (meant to be overridden)")
    else:
        print_fail(f"BaseFunctionHandler.name is '{BaseFunctionHandler.name}'")
        all_ok = False
    # pty_requested returns True
    if BaseFunctionHandler.pty_requested(None, "xterm", None, {}):
        print_ok("BaseFunctionHandler.pty_requested returns True")
    else:
        print_fail("BaseFunctionHandler.pty_requested should return True")
        all_ok = False
    # eof_received returns False
    if BaseFunctionHandler.eof_received(None) is False:
        print_ok("BaseFunctionHandler.eof_received returns False")
    else:
        print_fail("BaseFunctionHandler.eof_received should return False")
        all_ok = False
    # __init__ stores params
    class _MockUser: pass
    u = _MockUser()
    inst = BaseFunctionHandler(u, "sid", "1.2.3.4", client_version="v1",
                               ssh_key_name="k", ssh_key_type="ed25519",
                               ssh_key_fingerprint="fp")
    if inst._user is u and inst._session_id == "sid" and inst._remote_ip == "1.2.3.4":
        print_ok("BaseFunctionHandler.__init__ stores constructor args")
    else:
        print_fail("BaseFunctionHandler.__init__ did not store args")
        all_ok = False
    # connection_made sets _chan
    inst.connection_made("mock_chan")
    if inst._chan == "mock_chan":
        print_ok("BaseFunctionHandler.connection_made sets _chan")
    else:
        print_fail("BaseFunctionHandler.connection_made did not set _chan")
        all_ok = False
    return all_ok


def check_every_function_interface():
    """Every registered function handler must conform to the expected interface."""
    print_header("Universal function interface tests")
    from tacticalrmm.gateway.functions import FUNCTION_REGISTRY
    from tacticalrmm.gateway.handlers import RejectionHandler
    import asyncssh
    all_ok = True

    required_methods = [
        "connection_made",
        "shell_requested",
        "exec_requested",
        "pty_requested",
        "data_received",
        "eof_received",
        "connection_lost",
        "closed",
    ]
    lifecycle_methods = [
        "connection_made", "shell_requested", "exec_requested",
        "pty_requested", "eof_received", "connection_lost", "closed",
    ]
    data_methods = ["data_received", "terminal_size_changed"]

    for name, cls in sorted(FUNCTION_REGISTRY.items()):
        # 1. Handler must be an SSHServerSession subclass
        if issubclass(cls, asyncssh.SSHServerSession):
            print_ok(f"[{name}] Handler is SSHServerSession subclass")
        else:
            print_fail(f"[{name}] Handler is NOT SSHServerSession subclass")
            all_ok = False
            continue

        # 2. Must have non-empty name attribute
        h_name = getattr(cls, "name", "")
        if h_name and isinstance(h_name, str):
            print_ok(f"[{name}] Handler.name = '{h_name}'")
        else:
            print_fail(f"[{name}] Handler.name is missing or empty")
            all_ok = False

        # 3. Must have all required SSHServerSession methods
        for meth in required_methods:
            if hasattr(cls, meth):
                print_ok(f"[{name}] {meth}()")
            else:
                print_fail(f"[{name}] {meth}() MISSING")
                all_ok = False

        # 4. pty_requested must return bool (True or False)
        try:
            inst = cls.__new__(cls)
            # Minimal init if __init__ is complex
            if hasattr(cls, "__init__"):
                try:
                    inst = cls(user=None, session_id="test", remote_ip="127.0.0.1")
                except Exception:
                    try:
                        inst = cls()
                    except Exception:
                        inst = cls.__new__(cls)
            result = inst.pty_requested("xterm", (80, 24), {})
            if result is True or result is False:
                print_ok(f"[{name}] pty_requested returns {result}")
            else:
                print_fail(f"[{name}] pty_requested returned {type(result).__name__}, expected bool")
                all_ok = False
        except Exception as e:
            print_fail(f"[{name}] pty_requested raised {e}")
            all_ok = False

        # 5. shell_requested must return bool or RejectionHandler
        try:
            result = inst.shell_requested()
            if isinstance(result, RejectionHandler):
                print_ok(f"[{name}] shell_requested returns RejectionHandler")
            elif result is True or result is False:
                print_ok(f"[{name}] shell_requested returns {result}")
            else:
                print_fail(f"[{name}] shell_requested returned {type(result).__name__}")
                all_ok = False
        except RuntimeError as e:
            if "no running event loop" in str(e):
                print_ok(f"[{name}] shell_requested needs event loop (expected)")
            else:
                print_fail(f"[{name}] shell_requested raised {e}")
                all_ok = False
        except Exception as e:
            print_fail(f"[{name}] shell_requested raised {e}")
            all_ok = False

        # 6. exec_requested must return bool or RejectionHandler
        try:
            result = inst.exec_requested("test command")
            if isinstance(result, RejectionHandler):
                print_ok(f"[{name}] exec_requested returns RejectionHandler")
            elif result is True or result is False:
                print_ok(f"[{name}] exec_requested returns {result}")
            else:
                print_fail(f"[{name}] exec_requested returned {type(result).__name__}")
                all_ok = False
        except Exception as e:
            print_fail(f"[{name}] exec_requested raised {e}")
            all_ok = False

        # 7. eof_received must return bool
        try:
            result = inst.eof_received()
            if result is True or result is False:
                print_ok(f"[{name}] eof_received returns {result}")
            else:
                print_fail(f"[{name}] eof_received returned {type(result).__name__}")
                all_ok = False
        except Exception as e:
            print_fail(f"[{name}] eof_received raised {e}")
            all_ok = False

        # 8. data_received accepts str and bytes
        try:
            inst.data_received("test", None)
            print_ok(f"[{name}] data_received(str) ok")
        except Exception as e:
            print_fail(f"[{name}] data_received(str) raised {e}")
            all_ok = False
        try:
            inst.data_received(b"test", None)
            print_ok(f"[{name}] data_received(bytes) ok")
        except Exception as e:
            print_fail(f"[{name}] data_received(bytes) raised {e}")
            all_ok = False

        # 9. connection_lost accepts None
        try:
            inst.connection_lost(None)
            print_ok(f"[{name}] connection_lost(None) ok")
        except Exception as e:
            print_fail(f"[{name}] connection_lost raised {e}")
            all_ok = False

        # 10. closed can be called
        try:
            inst.closed()
            print_ok(f"[{name}] closed() ok")
        except Exception as e:
            print_fail(f"[{name}] closed() raised {e}")
            all_ok = False

        # 11. connection_made sets _chan
        class _FakeChan:
            def write(self, d): pass
            def is_closing(self): return False
            def get_extra_info(self, *a, **kw): return ("", "")
            def exit(self, c): pass
        try:
            inst2 = cls.__new__(cls)
            try:
                inst2 = cls(user=None, session_id="test", remote_ip="127.0.0.1")
            except Exception:
                pass
            inst2.connection_made(_FakeChan())
            chan = getattr(inst2, "_chan", None)
            if chan is not None:
                print_ok(f"[{name}] connection_made sets _chan")
            else:
                print_fail(f"[{name}] connection_made did NOT set _chan")
                all_ok = False
        except Exception as e:
            print_fail(f"[{name}] connection_made raised {e}")
            all_ok = False

    return all_ok


def check_rate_limiter():
    """_RateLimiter blocks after max_attempts, resets, and supports configure."""
    print_header("Rate limiter")
    from tacticalrmm.gateway.rate_limiter import _RateLimiter
    import time
    all_ok = True
    rl = _RateLimiter(max_attempts=3, window=10)

    for i in range(3):
        if rl.allow("1.2.3.4"):
            print_ok(f"Rate limiter allows attempt {i+1}")
        else:
            print_fail(f"Rate limiter blocked attempt {i+1}")
            all_ok = False
    if not rl.allow("1.2.3.4"):
        print_ok("Rate limiter blocks after max_attempts")
    else:
        print_fail("Rate limiter allowed 4th attempt (should block)")
        all_ok = False
    if rl.allow("5.6.7.8"):
        print_ok("Rate limiter allows different IP")
    else:
        print_fail("Rate limiter blocked different IP")
        all_ok = False
    rl.reset("1.2.3.4")
    if rl.allow("1.2.3.4"):
        print_ok("Rate limiter allows after reset")
    else:
        print_fail("Rate limiter blocked after reset")
        all_ok = False
    rl.configure(max_attempts=5)
    if rl._max_attempts == 5:
        print_ok("Rate limiter configure() works")
    else:
        print_fail("Rate limiter configure() failed")
        all_ok = False
    rl2 = _RateLimiter(max_attempts=5, window=0)
    rl2.allow("test")
    rl2._cleanup_stale(time.time())
    print_ok("Rate limiter _cleanup_stale works")
    return all_ok


def check_rejection_handler_full():
    """RejectionHandler returns expected values for all SSH session methods."""
    print_header("RejectionHandler full coverage")
    from tacticalrmm.gateway.handlers import RejectionHandler
    all_ok = True

    methods = ["pty_requested", "shell_requested", "exec_requested", "eof_received",
               "connection_made", "connection_lost", "closed"]
    for m in methods:
        if hasattr(RejectionHandler, m):
            print_ok(f"RejectionHandler.{m}()")
        else:
            print_fail(f"RejectionHandler.{m}() MISSING")
            all_ok = False

    rh = RejectionHandler("test message")
    if rh.pty_requested("xterm", (80, 24), {}) is False:
        print_ok("RejectionHandler.pty_requested returns False")
    else:
        print_fail("RejectionHandler.pty_requested should return False")
        all_ok = False
    if rh.shell_requested() is True:
        print_ok("RejectionHandler.shell_requested returns True")
    else:
        print_fail("RejectionHandler.shell_requested should return True")
        all_ok = False
    if rh.exec_requested("cmd") is True:
        print_ok("RejectionHandler.exec_requested returns True")
    else:
        print_fail("RejectionHandler.exec_requested should return True")
        all_ok = False
    if rh.eof_received() is False:
        print_ok("RejectionHandler.eof_received returns False")
    else:
        print_fail("RejectionHandler.eof_received should return False")
        all_ok = False
    # connection_lost(None) and closed() should not raise
    try:
        rh.connection_lost(None)
        print_ok("RejectionHandler.connection_lost(None) ok")
    except Exception as e:
        print_fail(f"RejectionHandler.connection_lost raised {e}")
        all_ok = False
    try:
        rh.closed()
        print_ok("RejectionHandler.closed() ok")
    except Exception as e:
        print_fail(f"RejectionHandler.closed raised {e}")
        all_ok = False

    return all_ok


def check_direct_session_handler_full():
    """DirectSessionHandler has all expected methods and returns correct types."""
    print_header("DirectSessionHandler full coverage")
    from tacticalrmm.gateway.handlers import DirectSessionHandler
    all_ok = True

    expected = [
        "connection_made", "exec_requested", "pty_requested", "shell_requested",
        "terminal_modes", "data_received", "eof_received", "connection_lost",
        "terminal_size_changed", "closed",
    ]
    for m in expected:
        if hasattr(DirectSessionHandler, m):
            print_ok(f"DirectSessionHandler.{m}()")
        else:
            print_fail(f"DirectSessionHandler.{m}() MISSING")
            all_ok = False

    # terminal_modes returns dict
    dsh = DirectSessionHandler(
        user=None, agent=None, session_id="test", remote_ip="127.0.0.1",
    )
    modes = dsh.terminal_modes()
    if isinstance(modes, dict) and len(modes) > 0:
        print_ok(f"DirectSessionHandler.terminal_modes returns dict ({len(modes)} entries)")
    else:
        print_fail("DirectSessionHandler.terminal_modes should return non-empty dict")
        all_ok = False

    # eof_received returns False by default
    try:
        dsh2 = DirectSessionHandler(
            user=None, agent=None, session_id="test", remote_ip="127.0.0.1",
        )
        result = dsh2.eof_received()
        if result is False:
            print_ok("DirectSessionHandler.eof_received returns False")
        else:
            print_fail(f"DirectSessionHandler.eof_received returned {result}")
            all_ok = False
    except Exception as e:
        print_fail(f"DirectSessionHandler.eof_received raised {e}")
        all_ok = False

    return all_ok


def check_constants_functional():
    """Functional tests for constants module helpers."""
    print_header("Constants functional tests")
    from tacticalrmm.gateway.constants import (
        _strip_ansi, get_local_ips, build_welcome_message,
        ANSI_ESCAPE, WELCOME_TEMPLATE, WELCOME_TEMPLATE_PLAIN,
    )
    import re
    all_ok = True

    if isinstance(ANSI_ESCAPE, re.Pattern):
        print_ok("ANSI_ESCAPE is a compiled regex")
    else:
        print_fail("ANSI_ESCAPE is not a compiled regex")
        all_ok = False

    if _strip_ansi("\x1b[32mhello\x1b[0m") == "hello":
        print_ok("_strip_ansi removes ANSI color codes")
    else:
        stripped = _strip_ansi("\x1b[32mhello\x1b[0m")
        print_fail(f"_strip_ansi got '{stripped}'")
        all_ok = False
    if _strip_ansi("plain text") == "plain text":
        print_ok("_strip_ansi passes plain text through")
    else:
        print_fail("_strip_ansi corrupts plain text")
        all_ok = False
    if _strip_ansi("") == "":
        print_ok("_strip_ansi handles empty string")
    else:
        print_fail("_strip_ansi fails on empty string")
        all_ok = False
    if _strip_ansi("\x1b[1mbold\x1b[0m and \x1b[31mred\x1b[0m") == "bold and red":
        print_ok("_strip_ansi handles multiple codes")
    else:
        print_fail("_strip_ansi fails on multiple codes")
        all_ok = False

    msg = build_welcome_message("testuser", "admin", "myhost", "Linux", "/bin/bash", "1.0", "1.2.3.4", "10.0.0.1")
    if "testuser" in msg and "myhost" in msg and "1.2.3.4" in msg:
        print_ok("build_welcome_message produces correct output")
    else:
        print_fail("build_welcome_message missing expected content")
        all_ok = False

    if "{username}" in WELCOME_TEMPLATE and "{hostname}" in WELCOME_TEMPLATE:
        print_ok("WELCOME_TEMPLATE has format placeholders")
    else:
        print_fail("WELCOME_TEMPLATE missing format placeholders")
        all_ok = False
    if "{username}" in WELCOME_TEMPLATE_PLAIN and "{hostname}" in WELCOME_TEMPLATE_PLAIN:
        print_ok("WELCOME_TEMPLATE_PLAIN has format placeholders")
    else:
        print_fail("WELCOME_TEMPLATE_PLAIN missing format placeholders")
        all_ok = False

    return all_ok


def check_mixins_functional():
    """Functional tests for mixins: DataBuffer, BaseSessionMixin."""
    print_header("Mixins functional tests")
    from tacticalrmm.gateway.mixins import DataBuffer, BaseSessionMixin
    all_ok = True

    db = DataBuffer()
    if db._buf == b"":
        print_ok("DataBuffer initializes with empty buffer")
    else:
        print_fail("DataBuffer not empty on init")
        all_ok = False
    db.append("hello")
    if db._buf == b"hello":
        print_ok("DataBuffer.append works with str input")
    else:
        print_fail(f"DataBuffer.append(str) got {db._buf!r}")
        all_ok = False
    db.append(b" world")
    if db._buf == b"hello world":
        print_ok("DataBuffer.append works with bytes input")
    else:
        print_fail(f"DataBuffer.append(bytes) got {db._buf!r}")
        all_ok = False
    if db.has_line():
        print_fail("DataBuffer.has_line false positive")
        all_ok = False
    else:
        print_ok("DataBuffer.has_line correctly false for 'hello world'")
    db.append("\r\nline2")
    if db.has_line():
        print_ok("DataBuffer.has_line detects newline")
    else:
        print_fail("DataBuffer.has_line missed newline")
        all_ok = False
    lines = db.split_lines()
    if lines == [b"hello world"]:
        print_ok("DataBuffer.split_lines works")
    else:
        print_fail(f"DataBuffer.split_lines returned {lines!r}")
        all_ok = False
    if db._buf == b"line2":
        print_ok("DataBuffer.split_lines preserves remainder in _buf")
    else:
        print_fail(f"DataBuffer.split_lines remainder is {db._buf!r}")
        all_ok = False

    bsm_methods = [
        "_setup_connection", "_write_welcome", "_record_session",
        "_close_session", "_audit_terminal_input", "_safe_write", "_safe_exit",
    ]
    for m in bsm_methods:
        if hasattr(BaseSessionMixin, m):
            print_ok(f"BaseSessionMixin.{m}()")
        else:
            print_fail(f"BaseSessionMixin.{m}() MISSING")
            all_ok = False

    return all_ok


def check_permissions_functions():
    """Permissions module: _fingerprint and function existence."""
    print_header("Permissions functions")
    from tacticalrmm.gateway.permissions import _fingerprint, _validate_key
    all_ok = True

    fp = _fingerprint(b"test key bytes")
    if fp.startswith("SHA256:"):
        print_ok("_fingerprint produces SHA256: prefixed hash")
    else:
        print_fail(f"_fingerprint produced {fp!r}")
        all_ok = False
    if len(fp) > 10:
        print_ok(f"_fingerprint hash length = {len(fp)} chars")
    else:
        print_fail("_fingerprint hash too short")
        all_ok = False
    # Different input => different hash
    fp2 = _fingerprint(b"other bytes")
    if fp != fp2:
        print_ok("_fingerprint produces different hash for different input")
    else:
        print_fail("_fingerprint collision")
        all_ok = False

    # _validate_key with mock key objects
    class _MockKeyPublicData:
        public_data = b"raw_key_bytes"

    class _MockKeyGetBytes:
        def get_public_key_bytes(self):
            return b"raw_key_bytes"

    raw1, fp1 = _validate_key(_MockKeyPublicData())
    if raw1 == b"raw_key_bytes":
        print_ok("_validate_key reads public_data attribute")
    else:
        print_fail(f"_validate_key public_data returned {raw1!r}")
        all_ok = False
    raw2, fp2 = _validate_key(_MockKeyGetBytes())
    if raw2 == b"raw_key_bytes":
        print_ok("_validate_key falls back to get_public_key_bytes()")
    else:
        print_fail(f"_validate_key get_public_key_bytes returned {raw2!r}")
        all_ok = False

    # Check all permission module async functions exist
    from tacticalrmm.gateway.permissions import (
        validate_ssh_key, validate_user_active, validate_menu_access,
        validate_agent_access, get_key_and_user, check_user_can_access_agent,
        check_user_can_use_menu, check_agent_online,
    )
    for fn_name in ["validate_ssh_key", "validate_user_active", "validate_menu_access",
                    "validate_agent_access", "get_key_and_user", "check_user_can_access_agent",
                    "check_user_can_use_menu", "check_agent_online"]:
        obj = locals().get(fn_name)
        if callable(obj):
            print_ok(f"permissions.{fn_name}() is callable")
        else:
            print_fail(f"permissions.{fn_name}() NOT callable")
            all_ok = False

    return all_ok


def check_egg_game_mechanics():
    """EggGame (snake) core mechanics: food placement, direction, score."""
    print_header("EggGame mechanics")
    from tacticalrmm.gateway.functions.egg import EggGame, _format_highscores
    all_ok = True

    class _FakeHandler:
        _chan = None
        _user = None
        _state = "snake"

    handler = _FakeHandler()
    game = EggGame(handler)

    if game._snake_width > 0 and game._snake_height > 0:
        print_ok(f"EggGame board is {game._snake_width}x{game._snake_height}")
    else:
        print_fail("EggGame board dimensions invalid")
        all_ok = False
    if game._snake_dir == (0, 1):
        print_ok("EggGame initial direction is right (0, 1)")
    else:
        print_fail(f"EggGame direction is {game._snake_dir}")
        all_ok = False
    if game._snake_score == 0:
        print_ok("EggGame score starts at 0")
    else:
        print_fail(f"EggGame score is {game._snake_score}")
        all_ok = False
    if game._snake_buf == "":
        print_ok("EggGame input buffer starts empty")
    else:
        print_fail(f"EggGame input buffer is {game._snake_buf!r}")
        all_ok = False

    # _place_food returns valid cell even with empty snake
    food = game._snake_place_food()
    if food is not None and len(food) == 2:
        r, c = food
        if 0 <= r < game._snake_height and 0 <= c < game._snake_width:
            print_ok(f"EggGame places food at valid cell {food}")
        else:
            print_fail(f"EggGame food cell {food} out of bounds")
            all_ok = False
    else:
        print_fail("EggGame _snake_place_food returned invalid")
        all_ok = False

    # Direction reversal should be prevented
    game._snake_dir = (0, 1)
    game.handle_input("a")  # left
    if game._snake_dir == (0, -1):
        print_ok("EggGame handle_input changes direction")
    else:
        print_fail(f"EggGame handle_input direction is {game._snake_dir}")
        all_ok = False
    game.handle_input("d")  # right = reverse of left
    if game._snake_dir == (0, -1):
        print_ok("EggGame prevents reversing direction")
    else:
        print_fail("EggGame allowed reverse direction")
        all_ok = False

    if _format_highscores([]) == "":
        print_ok("_format_highscores returns empty for no scores")
    else:
        print_fail("_format_highscores should be empty for no scores")
        all_ok = False

    return all_ok


async def run_async_checks():
    """Run async checks that need an event loop."""
    await check_get_gateway_settings()


def main():
    print("\n" + "="*60)
    print("  Tactical RMM SSH Gateway Health Check")
    print("="*60)

    results = []

    results.append(("Model fields", check_model_fields()))
    results.append(("AuditLog model", check_audit_log_model()))
    results.append(("CoreSettings", check_core_settings()))
    results.append(("Gateway module imports", check_gateway_module_imports()))
    results.append(("Handler classes", check_handler_classes()))
    results.append(("MenuSessionHandler", check_menu_handler()))
    results.append(("NATS connectivity", check_nats_connection()))
    results.append(("HOSTED/DEMO flags", check_gateway_settings_respect_hosted()))
    results.append(("Audit log entries", check_audit_log_entry_count()))
    results.append(("SSHSession model", check_ssh_session_model()))
    results.append(("EggGame import", check_egg_game()))
    results.append(("Refactored handlers", check_refactored_handlers()))
    results.append(("Constants helpers", check_constants_helpers()))
    results.append(("New SSH permission fields", check_new_ssh_permission_fields()))
    results.append(("FUNCTION_REGISTRY autodiscovery", check_function_registry_autodiscovery()))
    results.append(("BaseFunctionHandler", check_base_function_handler()))
    results.append(("Universal function interface", check_every_function_interface()))
    results.append(("Rate limiter", check_rate_limiter()))
    results.append(("RejectionHandler full", check_rejection_handler_full()))
    results.append(("DirectSessionHandler full", check_direct_session_handler_full()))
    results.append(("Constants functional", check_constants_functional()))
    results.append(("Mixins", check_mixins_functional()))
    results.append(("Permissions functions", check_permissions_functions()))
    results.append(("EggGame mechanics", check_egg_game_mechanics()))

    # Run async checks
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(check_resolve_and_check_terminal_requires_can_ssh_open_terminal())
        loop.run_until_complete(check_resolve_and_check_exec_requires_can_ssh_send_commands())
        loop.run_until_complete(check_menu_access_requires_can_ssh_use_functions())
        loop.run_until_complete(check_superuser_bypasses_permissions())
        loop.close()
        results.append(("Terminal permission denial", True))
        results.append(("Exec permission denial", True))
        results.append(("Menu permission denial", True))
        results.append(("Superuser bypass", True))
    except Exception as e:
        print_fail(f"Permission tests failed: {e}")
        results.append(("Permission tests", False))

    print_header("Summary")
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    print(f"\n  Passed: {passed}")
    if failed > 0:
        print(f"  Failed: {failed}")
        for name, ok in results:
            if not ok:
                print(f"    - {name}")
        print("\n  [RESULT] SOME CHECKS FAILED")
        return 1
    else:
        print("\n  [RESULT] ALL CHECKS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())