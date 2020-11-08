from rest_framework.serializers import ModelSerializer, ReadOnlyField, ValidationError
from .models import Client, Site, Deployment


class SiteSerializer(ModelSerializer):
    client_name = ReadOnlyField(source="client.name")

    class Meta:
        model = Site
        fields = "__all__"

    def validate(self, val):
        if "|" in val["name"]:
            raise ValidationError("Site name cannot contain the | character")

        if self.context:
            client = Client.objects.get(pk=self.context["clientpk"])
            if Site.objects.filter(client=client, name=val["name"]).exists():
                raise ValidationError(f"Site {val['name']} already exists")

        return val


class ClientSerializer(ModelSerializer):
    sites = SiteSerializer(many=True, read_only=True)

    class Meta:
        model = Client
        fields = "__all__"

    def validate(self, val):

        if "site" in self.context:
            if "|" in self.context["site"]:
                raise ValidationError("Site name cannot contain the | character")
            if len(self.context["site"]) > 255:
                raise ValidationError("Site name too long")

        if "|" in val["name"]:
            raise ValidationError("Client name cannot contain the | character")

        return val


class SiteTreeSerializer(ModelSerializer):
    maintenance_mode = ReadOnlyField(source="has_maintenanace_mode_agents")
    failing_checks = ReadOnlyField(source="has_failing_checks")

    class Meta:
        model = Site
        fields = "__all__"
        ordering = ("failing_checks",)


class ClientTreeSerializer(ModelSerializer):
    sites = SiteTreeSerializer(many=True, read_only=True)
    maintenance_mode = ReadOnlyField(source="has_maintenanace_mode_agents")
    failing_checks = ReadOnlyField(source="has_failing_checks")

    class Meta:
        model = Client
        fields = "__all__"
        ordering = ("failing_checks",)


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
            "arch",
            "expiry",
            "install_flags",
        ]
