import logging

import requests as http_requests
from django.http import JsonResponse
from python_ipware import IpWare

from .models import (
    FirewallCountryRule,
    FirewallIPRule,
    FirewallLog,
    FirewallSettings,
)

logger = logging.getLogger("trmm")

# Paths that should always bypass the firewall (agent comms, health checks)
AGENT_API_PREFIXES = ("/api/v3/", "/api/v4/")
ALWAYS_ALLOWED_PATHS = ("/", "")

# Paths that must never be blocked regardless of firewall settings.
# .well-known is used by Let's Encrypt HTTP-01 challenges (TRMM defaults to
# DNS-01 but operators may switch).  /core/status and /core/v2/status are the
# unauthenticated monitoring endpoints.
BYPASS_PREFIXES = (
    "/.well-known/",
    "/core/status/",
    "/core/v2/status/",
)


class FirewallMiddleware:
    """Application-level firewall middleware.

    Intercepts HTTP requests and blocks based on IP rules and/or GeoIP country
    rules. Adapted from HuduGlue's FirewallMiddleware for the Tactical RMM
    DRF-based architecture.

    Placement: after AuthenticationMiddleware so we can check staff status.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            fw_settings = FirewallSettings.load()
        except Exception:
            # If we can't load settings, don't block anything
            return self.get_response(request)

        if not fw_settings.ip_firewall_enabled and not fw_settings.geoip_firewall_enabled:
            return self.get_response(request)

        client_ip = self._get_client_ip(request)
        if not client_ip:
            return self.get_response(request)

        # Staff bypass - only works for session-authenticated users (web UI).
        # DRF token auth (API keys) is resolved at the view layer, after
        # middleware, so token-authenticated admins are still subject to
        # IP/GeoIP rules.  This is intentional: API keys should be scoped
        # by network policy, not silently exempted.
        if fw_settings.staff_bypass and self._is_staff(request):
            return self.get_response(request)

        # API bypass (agent communication endpoints)
        if fw_settings.api_bypass and request.path.startswith(AGENT_API_PREFIXES):
            return self.get_response(request)

        # Always allow root path and critical infrastructure paths
        if request.path in ALWAYS_ALLOWED_PATHS:
            return self.get_response(request)

        # Never block Let's Encrypt ACME challenges or monitoring endpoints
        if request.path.startswith(BYPASS_PREFIXES):
            return self.get_response(request)

        # IP firewall check
        if fw_settings.ip_firewall_enabled:
            blocked, reason = self._check_ip_firewall(client_ip, fw_settings)
            if blocked:
                self._log_block(
                    fw_settings, client_ip, reason, "", "", request
                )
                return self._blocked_response(reason)

        # GeoIP firewall check
        if fw_settings.geoip_firewall_enabled:
            blocked, reason, country_code, country_name = (
                self._check_geoip_firewall(client_ip, fw_settings)
            )
            if blocked:
                self._log_block(
                    fw_settings,
                    client_ip,
                    reason,
                    country_code,
                    country_name,
                    request,
                )
                return self._blocked_response(reason)

        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP using python-ipware (already used by TRMM)."""
        # Prefer the IP already extracted by LogIPMiddleware
        if hasattr(request, "_client_ip") and request._client_ip:
            return request._client_ip
        ipw = IpWare()
        client_ip, _ = ipw.get_client_ip(request.META)
        return str(client_ip) if client_ip else None

    @staticmethod
    def _is_staff(request):
        """Check if the current user is authenticated staff/superuser."""
        return (
            hasattr(request, "user")
            and request.user
            and hasattr(request.user, "is_authenticated")
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )

    @staticmethod
    def _check_ip_firewall(client_ip, fw_settings):
        """Check IP against active IP rules.

        Returns (blocked: bool, reason: str).
        """
        rules = FirewallIPRule.objects.filter(is_active=True)
        matches_rule = any(rule.matches_ip(client_ip) for rule in rules)

        if fw_settings.ip_firewall_mode == "blocklist":
            if matches_rule:
                return True, "ip_blocklist"
        else:  # allowlist
            if not matches_rule:
                return True, "ip_not_in_allowlist"

        return False, ""

    def _check_geoip_firewall(self, client_ip, fw_settings):
        """Check IP's country against active country rules.

        Returns (blocked, reason, country_code, country_name).
        """
        country_code, country_name = self._geoip_lookup(client_ip)

        if not country_code:
            # Fail-closed in allowlist mode, fail-open in blocklist mode
            if fw_settings.geoip_firewall_mode == "allowlist":
                return True, "geoip_lookup_failed", "", ""
            return False, "", "", ""

        rules = FirewallCountryRule.objects.filter(is_active=True)
        matches_rule = rules.filter(country_code=country_code).exists()

        if fw_settings.geoip_firewall_mode == "blocklist":
            if matches_rule:
                return True, "country_blocklist", country_code, country_name
        else:  # allowlist
            if not matches_rule:
                return (
                    True,
                    "country_not_in_allowlist",
                    country_code,
                    country_name,
                )

        return False, "", country_code, country_name

    @staticmethod
    def _geoip_lookup(ip_address):
        """Lookup country for an IP using ip-api.com (free, no key required).

        Returns (country_code, country_name) or ("", "") on failure.
        """
        import ipaddress as _ipaddress

        # Validate ip_address is a real IP before interpolating into a URL
        # to prevent SSRF via spoofed X-Forwarded-For or user input.
        try:
            _ipaddress.ip_address(ip_address)
        except (ValueError, TypeError):
            logger.warning("GeoIP lookup rejected non-IP value: %s", ip_address)
            return "", ""

        try:
            response = http_requests.get(
                f"http://ip-api.com/json/{ip_address}",
                params={"fields": "status,countryCode,country"},
                timeout=3,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return data.get("countryCode", ""), data.get("country", "")
        except Exception as e:
            logger.warning("GeoIP lookup failed for %s: %s", ip_address, e)

        return "", ""

    # Maximum number of log entries to keep (prevents unbounded DB growth from
    # flood attacks). When exceeded, the oldest 10% are pruned.
    MAX_LOG_ENTRIES = 10000

    @staticmethod
    def _log_block(fw_settings, client_ip, reason, country_code, country_name, request):
        """Create a FirewallLog entry if logging is enabled."""
        if not fw_settings.logging_enabled:
            return

        FirewallLog.objects.create(
            ip_address=client_ip,
            country_code=country_code,
            country_name=country_name,
            block_reason=reason,
            request_path=request.path[:500],
            request_method=request.method,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
        )

        # Prune old entries if the table has grown too large
        count = FirewallLog.objects.count()
        if count > FirewallMiddleware.MAX_LOG_ENTRIES:
            cutoff_id = (
                FirewallLog.objects.order_by("-timestamp")
                .values_list("id", flat=True)[FirewallMiddleware.MAX_LOG_ENTRIES - 1]
            )
            FirewallLog.objects.filter(id__lt=cutoff_id).delete()

    @staticmethod
    def _blocked_response(reason):
        """Return a JSON 403 response for blocked requests."""
        return JsonResponse(
            {"error": "Access denied by firewall", "reason": reason},
            status=403,
        )
