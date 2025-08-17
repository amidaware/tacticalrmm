import django_filters
from agents.models import Agent


class AgentFilter(django_filters.FilterSet):
    last_seen_range = django_filters.DateTimeFromToRangeFilter(field_name="last_seen")
    total_ram_range = django_filters.NumericRangeFilter(field_name="total_ram")
    patches_last_installed_range = django_filters.DateTimeFromToRangeFilter(
        field_name="patches_last_installed"
    )

    client_id = django_filters.NumberFilter(method="client_id_filter")

    class Meta:
        model = Agent
        fields = [
            "id",
            "hostname",
            "agent_id",
            "operating_system",
            "plat",
            "monitoring_type",
            "needs_reboot",
            "logged_in_username",
            "last_logged_in_user",
            "alert_template",
            "site",
            "policy",
            "last_seen_range",
            "total_ram_range",
            "patches_last_installed_range",
        ]

    def client_id_filter(self, queryset, name, value):
        if value:
            return queryset.filter(site__client__id=value)
        return queryset
