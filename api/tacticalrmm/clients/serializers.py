from rest_framework.serializers import (
    ModelSerializer,
    ReadOnlyField,
    SerializerMethodField,
    ValidationError,
)

from .models import Client, ClientCustomField, Deployment, Site, SiteCustomField


class SiteCustomFieldSerializer(ModelSerializer):
    class Meta:
        model = SiteCustomField
        fields = (
            "id",
            "field",
            "site",
            "value",
            "string_value",
            "bool_value",
            "multiple_value",
        )
        extra_kwargs = {
            "string_value": {"write_only": True},
            "bool_value": {"write_only": True},
            "multiple_value": {"write_only": True},
        }


class SiteSerializer(ModelSerializer):
    client_name = ReadOnlyField(source="client.name")
    custom_fields = SiteCustomFieldSerializer(many=True, read_only=True)
    maintenance_mode = ReadOnlyField()
    agent_count = ReadOnlyField()

    class Meta:
        model = Site
        fields = (
            "id",
            "name",
            "server_policy",
            "workstation_policy",
            "alert_template",
            "client_name",
            "client",
            "custom_fields",
            "agent_count",
            "block_policy_inheritance",
            "maintenance_mode",
            "failing_checks",
        )

    def validate(self, val):
        if "name" in val.keys() and "|" in val["name"]:
            raise ValidationError("Site name cannot contain the | character")

        return val


class SiteMinimumSerializer(ModelSerializer):
    client_name = ReadOnlyField(source="client.name")

    class Meta:
        model = Site
        fields = "__all__"


class ClientMinimumSerializer(ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"


class ClientCustomFieldSerializer(ModelSerializer):
    class Meta:
        model = ClientCustomField
        fields = (
            "id",
            "field",
            "client",
            "value",
            "string_value",
            "bool_value",
            "multiple_value",
        )
        extra_kwargs = {
            "string_value": {"write_only": True},
            "bool_value": {"write_only": True},
            "multiple_value": {"write_only": True},
        }


class ClientSerializer(ModelSerializer):
    sites = SerializerMethodField()
    custom_fields = ClientCustomFieldSerializer(many=True, read_only=True)
    maintenance_mode = ReadOnlyField()
    agent_count = ReadOnlyField()

    def get_sites(self, obj):
        return SiteSerializer(
            obj.filtered_sites,
            many=True,
        ).data

    class Meta:
        model = Client
        fields = (
            "id",
            "name",
            "server_policy",
            "workstation_policy",
            "alert_template",
            "block_policy_inheritance",
            "sites",
            "custom_fields",
            "agent_count",
            "maintenance_mode",
            "failing_checks",
        )

    def validate(self, val):
        if "name" in val.keys() and "|" in val["name"]:
            raise ValidationError("Client name cannot contain the | character")

        return val


class DeploymentSerializer(ModelSerializer):
    client_id = ReadOnlyField(source="client.id")
    site_id = ReadOnlyField(source="site.id")
    client_name = ReadOnlyField(source="client.name")
    site_name = ReadOnlyField(source="site.name")

    class Meta:
        model = Deployment
        fields = [
            "id",
            "uid",
            "client_id",
            "site_id",
            "client_name",
            "site_name",
            "mon_type",
            "goarch",
            "expiry",
            "install_flags",
            "created",
        ]


class SiteAuditSerializer(ModelSerializer):
    class Meta:
        model = Site
        fields = "__all__"


class ClientAuditSerializer(ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"
