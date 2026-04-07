import django_filters

from scripts.models import Script


class ScriptFilter(django_filters.FilterSet):
    supported_platforms = django_filters.BaseInFilter(
        method="filter_supported_platforms"
    )

    class Meta:
        model = Script
        fields = [
            "script_type",
            "shell",
            "category",
            "favorite",
            "hidden",
            "run_as_user",
        ]

    def filter_supported_platforms(self, queryset, name, value):
        from django.db.models import Q

        q = Q()
        for platform in value:
            q |= Q(supported_platforms__contains=[platform])
        return queryset.filter(q)
