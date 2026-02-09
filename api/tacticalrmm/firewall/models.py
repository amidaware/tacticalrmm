import ipaddress
import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger("trmm")


class FirewallSettings(models.Model):
    """Singleton model for firewall configuration.
    Adapted from HuduGlue's FirewallSettings pattern.
    """

    ip_firewall_enabled = models.BooleanField(default=False)
    ip_firewall_mode = models.CharField(
        max_length=20,
        choices=[("blocklist", "Blocklist"), ("allowlist", "Allowlist")],
        default="blocklist",
    )
    geoip_firewall_enabled = models.BooleanField(default=False)
    geoip_firewall_mode = models.CharField(
        max_length=20,
        choices=[("blocklist", "Blocklist"), ("allowlist", "Allowlist")],
        default="blocklist",
    )
    staff_bypass = models.BooleanField(
        default=True,
        help_text="Allow staff/superusers to bypass firewall rules",
    )
    api_bypass = models.BooleanField(
        default=True,
        help_text="Allow API endpoints (agent comms) to bypass firewall rules",
    )
    logging_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Firewall Settings"
        verbose_name_plural = "Firewall Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Firewall Settings"


class FirewallIPRule(models.Model):
    """IP-based firewall rule supporting single IPs and CIDR notation."""

    ip_address = models.CharField(
        max_length=45,
        help_text="IPv4/IPv6 address or CIDR notation (e.g. 192.168.1.0/24)",
    )
    description = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="firewall_ip_rules",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ip_address} ({'active' if self.is_active else 'inactive'})"

    def matches_ip(self, client_ip: str) -> bool:
        """Check if the given IP matches this rule (supports CIDR)."""
        try:
            if "/" in self.ip_address:
                return ipaddress.ip_address(client_ip) in ipaddress.ip_network(
                    self.ip_address, strict=False
                )
            return client_ip == self.ip_address
        except ValueError:
            logger.warning(
                "Invalid IP comparison: rule=%s client=%s",
                self.ip_address,
                client_ip,
            )
            return False


class FirewallCountryRule(models.Model):
    """Country-based firewall rule using ISO 3166-1 alpha-2 country codes."""

    country_code = models.CharField(max_length=2)
    country_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="firewall_country_rules",
    )

    class Meta:
        ordering = ["country_name"]

    def __str__(self):
        return f"{self.country_name} ({self.country_code})"


class FirewallLog(models.Model):
    """Log entry for blocked requests."""

    BLOCK_REASONS = [
        ("ip_blocklist", "IP Blocklist"),
        ("ip_not_in_allowlist", "IP Not In Allowlist"),
        ("country_blocklist", "Country Blocklist"),
        ("country_not_in_allowlist", "Country Not In Allowlist"),
        ("geoip_lookup_failed", "GeoIP Lookup Failed"),
    ]

    ip_address = models.CharField(max_length=45)
    country_code = models.CharField(max_length=2, blank=True, default="")
    country_name = models.CharField(max_length=100, blank=True, default="")
    block_reason = models.CharField(max_length=30, choices=BLOCK_REASONS)
    request_path = models.CharField(max_length=500)
    request_method = models.CharField(max_length=10)
    user_agent = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.ip_address} blocked ({self.block_reason}) at {self.timestamp}"
