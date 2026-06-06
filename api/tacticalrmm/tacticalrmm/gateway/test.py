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
from tacticalrmm.gateway.menu import MenuSessionHandler
from tacticalrmm.gateway.utils import _lookup_key, _resolve_and_check, _get_gateway_settings
from tacticalrmm.gateway.audit import (
    _audit_session_failed, _audit_exec_command, _audit_terminal_command,
    _record_session_and_audit, _close_session_and_audit,
)


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
        "tacticalrmm.gateway.menu",
        "tacticalrmm.gateway.audit",
        "tacticalrmm.gateway.exec",
        "tacticalrmm.gateway.terminal",
        "tacticalrmm.gateway.utils",
        "tacticalrmm.gateway.rate_limiter",
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
        from gateway.egg import EggGame, _add_highscore, _format_highscores
        print_ok("EggGame and highscore helpers import cleanly")
        return True
    except Exception as e:
        print_fail(f"EggGame import failed: {e}")
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

    # Run async checks
    try:
        asyncio.run(run_async_checks())
        results.append(("_get_gateway_settings", True))
    except Exception as e:
        print_fail(f"Async check failed: {e}")
        results.append(("_get_gateway_settings", False))

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