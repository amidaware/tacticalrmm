import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FirewallSettings",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("ip_firewall_enabled", models.BooleanField(default=False)),
                (
                    "ip_firewall_mode",
                    models.CharField(
                        choices=[
                            ("blocklist", "Blocklist"),
                            ("allowlist", "Allowlist"),
                        ],
                        default="blocklist",
                        max_length=20,
                    ),
                ),
                ("geoip_firewall_enabled", models.BooleanField(default=False)),
                (
                    "geoip_firewall_mode",
                    models.CharField(
                        choices=[
                            ("blocklist", "Blocklist"),
                            ("allowlist", "Allowlist"),
                        ],
                        default="blocklist",
                        max_length=20,
                    ),
                ),
                (
                    "staff_bypass",
                    models.BooleanField(
                        default=True,
                        help_text="Allow staff/superusers to bypass firewall rules",
                    ),
                ),
                (
                    "api_bypass",
                    models.BooleanField(
                        default=True,
                        help_text="Allow API endpoints (agent comms) to bypass firewall rules",
                    ),
                ),
                ("logging_enabled", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Firewall Settings",
                "verbose_name_plural": "Firewall Settings",
            },
        ),
        migrations.CreateModel(
            name="FirewallIPRule",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "ip_address",
                    models.CharField(
                        help_text="IPv4/IPv6 address or CIDR notation (e.g. 192.168.1.0/24)",
                        max_length=45,
                    ),
                ),
                (
                    "description",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="firewall_ip_rules",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="FirewallCountryRule",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("country_code", models.CharField(max_length=2)),
                ("country_name", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="firewall_country_rules",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["country_name"],
            },
        ),
        migrations.CreateModel(
            name="FirewallLog",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("ip_address", models.CharField(max_length=45)),
                (
                    "country_code",
                    models.CharField(blank=True, default="", max_length=2),
                ),
                (
                    "country_name",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                (
                    "block_reason",
                    models.CharField(
                        choices=[
                            ("ip_blocklist", "IP Blocklist"),
                            ("ip_not_in_allowlist", "IP Not In Allowlist"),
                            ("country_blocklist", "Country Blocklist"),
                            (
                                "country_not_in_allowlist",
                                "Country Not In Allowlist",
                            ),
                            ("geoip_lookup_failed", "GeoIP Lookup Failed"),
                        ],
                        max_length=30,
                    ),
                ),
                ("request_path", models.CharField(max_length=500)),
                ("request_method", models.CharField(max_length=10)),
                ("user_agent", models.TextField(blank=True, default="")),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
    ]
