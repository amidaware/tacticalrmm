from django.contrib import admin

from .models import Alert, AlertTemplate

admin.site.register(Alert)
admin.site.register(AlertTemplate)
