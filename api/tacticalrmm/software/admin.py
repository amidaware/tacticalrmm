from django.contrib import admin
from .models import ChocoSoftware, ChocoLog, InstalledSoftware


class ChocoAdmin(admin.ModelAdmin):
    readonly_fields = ("added",)


class ChocoLogAdmin(admin.ModelAdmin):
    readonly_fields = ("time",)


admin.site.register(ChocoSoftware, ChocoAdmin)
admin.site.register(ChocoLog, ChocoLogAdmin)
admin.site.register(InstalledSoftware)
