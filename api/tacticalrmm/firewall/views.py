import logging
import re
import subprocess

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tacticalrmm.helpers import notify_error

from .models import FirewallCountryRule, FirewallIPRule, FirewallLog, FirewallSettings
from .permissions import Fail2BanPerms, FirewallPerms
from .serializers import (
    FirewallCountryRuleSerializer,
    FirewallIPRuleSerializer,
    FirewallLogSerializer,
    FirewallSettingsSerializer,
)

logger = logging.getLogger("trmm")

# Common countries for quick-add in the UI
COMMON_COUNTRIES = [
    {"code": "US", "name": "United States"},
    {"code": "GB", "name": "United Kingdom"},
    {"code": "CA", "name": "Canada"},
    {"code": "AU", "name": "Australia"},
    {"code": "DE", "name": "Germany"},
    {"code": "FR", "name": "France"},
    {"code": "CN", "name": "China"},
    {"code": "RU", "name": "Russia"},
    {"code": "IN", "name": "India"},
    {"code": "BR", "name": "Brazil"},
    {"code": "JP", "name": "Japan"},
    {"code": "KR", "name": "South Korea"},
    {"code": "NL", "name": "Netherlands"},
    {"code": "SE", "name": "Sweden"},
    {"code": "SG", "name": "Singapore"},
]

IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


# ==================== Firewall Settings ====================


class GetEditFirewallSettings(APIView):
    permission_classes = [IsAuthenticated, FirewallPerms]

    def get(self, request):
        settings = FirewallSettings.load()
        return Response(FirewallSettingsSerializer(settings).data)

    def put(self, request):
        settings = FirewallSettings.load()
        serializer = FirewallSettingsSerializer(
            instance=settings, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("Firewall settings updated")


# ==================== IP Rules ====================


class GetAddFirewallIPRules(APIView):
    permission_classes = [IsAuthenticated, FirewallPerms]

    def get(self, request):
        rules = FirewallIPRule.objects.select_related("created_by").all()
        return Response(FirewallIPRuleSerializer(rules, many=True).data)

    def post(self, request):
        serializer = FirewallIPRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response("IP rule added")


class UpdateDeleteFirewallIPRule(APIView):
    permission_classes = [IsAuthenticated, FirewallPerms]

    def put(self, request, pk):
        rule = get_object_or_404(FirewallIPRule, pk=pk)
        serializer = FirewallIPRuleSerializer(
            instance=rule, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("IP rule updated")

    def delete(self, request, pk):
        get_object_or_404(FirewallIPRule, pk=pk).delete()
        return Response("IP rule deleted")


class ToggleFirewallIPRule(APIView):
    permission_classes = [IsAuthenticated, FirewallPerms]

    def post(self, request, pk):
        rule = get_object_or_404(FirewallIPRule, pk=pk)
        rule.is_active = not rule.is_active
        rule.save(update_fields=["is_active"])
        state = "enabled" if rule.is_active else "disabled"
        return Response(f"IP rule {state}")


# ==================== Country Rules ====================


class GetAddFirewallCountryRules(APIView):
    permission_classes = [IsAuthenticated, FirewallPerms]

    def get(self, request):
        rules = FirewallCountryRule.objects.select_related("created_by").all()
        return Response(FirewallCountryRuleSerializer(rules, many=True).data)

    def post(self, request):
        serializer = FirewallCountryRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response("Country rule added")


class UpdateDeleteFirewallCountryRule(APIView):
    permission_classes = [IsAuthenticated, FirewallPerms]

    def put(self, request, pk):
        rule = get_object_or_404(FirewallCountryRule, pk=pk)
        serializer = FirewallCountryRuleSerializer(
            instance=rule, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("Country rule updated")

    def delete(self, request, pk):
        get_object_or_404(FirewallCountryRule, pk=pk).delete()
        return Response("Country rule deleted")


class ToggleFirewallCountryRule(APIView):
    permission_classes = [IsAuthenticated, FirewallPerms]

    def post(self, request, pk):
        rule = get_object_or_404(FirewallCountryRule, pk=pk)
        rule.is_active = not rule.is_active
        rule.save(update_fields=["is_active"])
        state = "enabled" if rule.is_active else "disabled"
        return Response(f"Country rule {state}")


@api_view(["GET"])
@permission_classes([IsAuthenticated, FirewallPerms])
def common_countries(request):
    """Return a list of common countries for quick-add."""
    return Response(COMMON_COUNTRIES)


# ==================== Firewall Logs ====================


class GetFirewallLogs(APIView):
    permission_classes = [IsAuthenticated, FirewallPerms]

    def get(self, request):
        limit = int(request.query_params.get("limit", 100))
        limit = min(limit, 500)
        logs = FirewallLog.objects.all()[:limit]
        return Response(FirewallLogSerializer(logs, many=True).data)

    def delete(self, request):
        count = FirewallLog.objects.count()
        FirewallLog.objects.all().delete()
        return Response(f"Cleared {count} firewall log entries")


@api_view(["GET"])
@permission_classes([IsAuthenticated, FirewallPerms])
def firewall_log_analytics(request):
    """Return firewall log analytics: totals, top blocked IPs, top countries."""
    now = djangotime.now()
    total = FirewallLog.objects.count()
    daily = FirewallLog.objects.filter(
        timestamp__gte=now - djangotime.timedelta(days=1)
    ).count()
    weekly = FirewallLog.objects.filter(
        timestamp__gte=now - djangotime.timedelta(days=7)
    ).count()

    top_ips = (
        FirewallLog.objects.values("ip_address")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    top_countries = (
        FirewallLog.objects.exclude(country_code="")
        .values("country_code", "country_name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    daily_counts = (
        FirewallLog.objects.filter(
            timestamp__gte=now - djangotime.timedelta(days=30)
        )
        .annotate(date=TruncDate("timestamp"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    return Response(
        {
            "total_blocks": total,
            "daily_blocks": daily,
            "weekly_blocks": weekly,
            "top_blocked_ips": list(top_ips),
            "top_blocked_countries": list(top_countries),
            "daily_counts": list(daily_counts),
        }
    )


# ==================== GeoIP Lookup ====================


@api_view(["POST"])
@permission_classes([IsAuthenticated, FirewallPerms])
def geoip_lookup(request):
    """Lookup GeoIP information for a given IP address."""
    ip = request.data.get("ip", "").strip()
    if not ip:
        return notify_error("IP address is required")

    from .middleware import FirewallMiddleware

    country_code, country_name = FirewallMiddleware._geoip_lookup(ip)
    if not country_code:
        return notify_error(f"Could not determine country for {ip}")

    return Response(
        {
            "ip": ip,
            "country_code": country_code,
            "country_name": country_name,
        }
    )


# ==================== Fail2Ban ====================


def _run_fail2ban_command(command):
    """Execute a fail2ban-client command via sudo.

    Returns (success: bool, stdout: str, stderr: str).
    """
    try:
        result = subprocess.run(
            ["sudo", "/usr/bin/fail2ban-client"] + command,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return False, "", "fail2ban-client not found"
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def _is_fail2ban_installed():
    """Check if fail2ban is installed."""
    try:
        result = subprocess.run(
            ["which", "fail2ban-client"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _is_fail2ban_running():
    """Check if fail2ban service is running."""
    try:
        result = subprocess.run(
            ["sudo", "/bin/systemctl", "status", "fail2ban"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


class Fail2BanStatus(APIView):
    """Get fail2ban status including all jails and banned IP counts."""

    permission_classes = [IsAuthenticated, Fail2BanPerms]

    def get(self, request):
        installed = _is_fail2ban_installed()
        if not installed:
            return Response(
                {
                    "installed": False,
                    "running": False,
                    "jails": [],
                }
            )

        running = _is_fail2ban_running()
        if not running:
            return Response(
                {
                    "installed": True,
                    "running": False,
                    "jails": [],
                }
            )

        # Get list of jails
        success, stdout, _ = _run_fail2ban_command(["status"])
        jails = []
        if success and stdout:
            for line in stdout.split("\n"):
                if "Jail list:" in line:
                    jail_names = [
                        j.strip() for j in line.split(":", 1)[1].split(",") if j.strip()
                    ]
                    for jail_name in jail_names:
                        jail_info = self._get_jail_info(jail_name)
                        jails.append(jail_info)

        return Response(
            {
                "installed": True,
                "running": True,
                "jails": jails,
            }
        )

    @staticmethod
    def _get_jail_info(jail_name):
        """Get detailed status for a single jail."""
        success, stdout, _ = _run_fail2ban_command(["status", jail_name])
        info = {
            "name": jail_name,
            "currently_banned": 0,
            "total_banned": 0,
            "banned_ips": [],
        }
        if success and stdout:
            for line in stdout.split("\n"):
                line = line.strip()
                if "Currently banned:" in line:
                    try:
                        info["currently_banned"] = int(line.split(":", 1)[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif "Total banned:" in line:
                    try:
                        info["total_banned"] = int(line.split(":", 1)[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif "Banned IP list:" in line:
                    ips = line.split(":", 1)[1].strip()
                    if ips:
                        info["banned_ips"] = [
                            ip.strip() for ip in ips.split() if ip.strip()
                        ]
        return info


@api_view(["POST"])
@permission_classes([IsAuthenticated, Fail2BanPerms])
def fail2ban_unban_ip(request):
    """Unban a specific IP from a specific jail."""
    ip = request.data.get("ip", "").strip()
    jail = request.data.get("jail", "").strip()

    if not ip or not jail:
        return notify_error("Both IP and jail name are required")

    if not IP_RE.match(ip):
        return notify_error("Invalid IP address format")

    success, stdout, stderr = _run_fail2ban_command(["set", jail, "unbanip", ip])
    if success:
        logger.info(
            "fail2ban: user %s unbanned %s from jail %s",
            request.user.username,
            ip,
            jail,
        )
        return Response(f"IP {ip} unbanned from {jail}")

    return notify_error(f"Failed to unban IP: {stderr}")


@api_view(["POST"])
@permission_classes([IsAuthenticated, Fail2BanPerms])
def fail2ban_unban_all(request):
    """Unban all IPs from a specific jail."""
    jail = request.data.get("jail", "").strip()
    if not jail:
        return notify_error("Jail name is required")

    success, stdout, stderr = _run_fail2ban_command(["set", jail, "unbanip", "--all"])
    if success:
        logger.info(
            "fail2ban: user %s unbanned all IPs from jail %s",
            request.user.username,
            jail,
        )
        return Response(f"All IPs unbanned from {jail}")

    return notify_error(f"Failed to unban all IPs: {stderr}")


@api_view(["POST"])
@permission_classes([IsAuthenticated, Fail2BanPerms])
def fail2ban_check_ip(request):
    """Check if a specific IP is banned in any jail."""
    ip = request.data.get("ip", "").strip()
    if not ip:
        return notify_error("IP address is required")

    if not IP_RE.match(ip):
        return notify_error("Invalid IP address format")

    # Get list of jails first
    success, stdout, _ = _run_fail2ban_command(["status"])
    if not success:
        return notify_error("Could not get fail2ban status")

    banned_in = []
    for line in stdout.split("\n"):
        if "Jail list:" in line:
            jail_names = [
                j.strip() for j in line.split(":", 1)[1].split(",") if j.strip()
            ]
            for jail_name in jail_names:
                ok, out, _ = _run_fail2ban_command(["status", jail_name])
                if ok and ip in out:
                    banned_in.append(jail_name)

    return Response(
        {
            "ip": ip,
            "is_banned": len(banned_in) > 0,
            "banned_in_jails": banned_in,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, Fail2BanPerms])
def fail2ban_start(request):
    """Enable and start the fail2ban service."""
    if not _is_fail2ban_installed():
        return notify_error("fail2ban is not installed")

    try:
        subprocess.run(
            ["sudo", "/bin/systemctl", "enable", "fail2ban"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        subprocess.run(
            ["sudo", "/bin/systemctl", "start", "fail2ban"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as e:
        return notify_error(f"Failed to start fail2ban: {e}")

    if _is_fail2ban_running():
        logger.info("fail2ban: user %s started the service", request.user.username)
        return Response("fail2ban service started")

    return notify_error("fail2ban service failed to start")


@api_view(["POST"])
@permission_classes([IsAuthenticated, Fail2BanPerms])
def fail2ban_install(request):
    """Install fail2ban via apt-get (Debian/Ubuntu only)."""
    if _is_fail2ban_installed():
        return Response("fail2ban is already installed")

    try:
        subprocess.run(
            ["sudo", "/usr/bin/apt-get", "update"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        result = subprocess.run(
            ["sudo", "/usr/bin/apt-get", "install", "-y", "fail2ban"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return notify_error(f"Installation failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        return notify_error("Installation timed out")
    except Exception as e:
        return notify_error(f"Installation error: {e}")

    if _is_fail2ban_installed():
        # Enable and start the service
        subprocess.run(
            ["sudo", "/bin/systemctl", "enable", "fail2ban"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        subprocess.run(
            ["sudo", "/bin/systemctl", "start", "fail2ban"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        logger.info("fail2ban: user %s installed fail2ban", request.user.username)
        return Response("fail2ban installed and started successfully")

    return notify_error("fail2ban installation appeared to fail")
