from django.contrib import admin

from .models import Alert, AlertTemplate, AlertExclusion


admin.site.register(Alert)
admin.site.register(AlertTemplate)
admin.site.register(AlertExclusion)