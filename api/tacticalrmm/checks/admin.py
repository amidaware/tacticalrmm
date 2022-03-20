from django.contrib import admin

from .models import Check, CheckHistory, PolicyCheckResult

admin.site.register(Check)
admin.site.register(CheckHistory)
admin.site.register(PolicyCheckResult)