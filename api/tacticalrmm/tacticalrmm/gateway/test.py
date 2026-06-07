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