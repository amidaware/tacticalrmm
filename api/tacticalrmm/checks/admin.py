from django.contrib import admin

from .models import Check, CheckHistory

admin.site.register(Check)
admin.site.register(CheckHistory)
