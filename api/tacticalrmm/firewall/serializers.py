import ipaddress

from rest_framework import serializers

from .models import FirewallCountryRule, FirewallIPRule, FirewallLog, FirewallSettings


class FirewallSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirewallSettings
        fields = [
            "ip_firewall_enabled",
            "ip_firewall_mode",
            "geoip_firewall_enabled",
            "geoip_firewall_mode",
            "staff_bypass",
            "api_bypass",
            "logging_enabled",
        ]


class FirewallIPRuleSerializer(serializers.ModelSerializer):
    created_by_username = serializers.SerializerMethodField()

    class Meta:
        model = FirewallIPRule
        fields = [
            "id",
            "ip_address",
            "description",
            "is_active",
            "created_at",
            "created_by",
            "created_by_username",
        ]
        read_only_fields = ["id", "created_at", "created_by", "created_by_username"]

    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else None

    def validate_ip_address(self, value):
        value = value.strip()
        try:
            if "/" in value:
                ipaddress.ip_network(value, strict=False)
            else:
                ipaddress.ip_address(value)
        except ValueError:
            raise serializers.ValidationError(
                "Invalid IP address or CIDR notation. "
                "Examples: 192.168.1.1, 10.0.0.0/8, 2001:db8::1"
            )
        return value


class FirewallCountryRuleSerializer(serializers.ModelSerializer):
    created_by_username = serializers.SerializerMethodField()

    class Meta:
        model = FirewallCountryRule
        fields = [
            "id",
            "country_code",
            "country_name",
            "is_active",
            "created_at",
            "created_by",
            "created_by_username",
        ]
        read_only_fields = ["id", "created_at", "created_by", "created_by_username"]

    def validate_country_code(self, value):
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError(
                "Country code must be a 2-letter ISO 3166-1 alpha-2 code (e.g. US, GB, DE)"
            )
        return value


class FirewallLogSerializer(serializers.ModelSerializer):
    block_reason_display = serializers.SerializerMethodField()

    class Meta:
        model = FirewallLog
        fields = [
            "id",
            "ip_address",
            "country_code",
            "country_name",
            "block_reason",
            "block_reason_display",
            "request_path",
            "request_method",
            "user_agent",
            "timestamp",
        ]

    def get_block_reason_display(self, obj):
        return obj.get_block_reason_display()
