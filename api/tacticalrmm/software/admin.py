from django.contrib import admin

from .models import ChocoSoftware, InstalledSoftware


class ChocoAdmin(admin.ModelAdmin):
    readonly_fields = ("added",)


admin.site.register(ChocoSoftware, ChocoAdmin)
admin.site.register(InstalledSoftware)
