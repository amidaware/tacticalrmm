from django.contrib import admin

from .models import AuditLog, PendingAction, DebugLog

admin.site.register(PendingAction)
admin.site.register(AuditLog)
admin.site.register(DebugLog)
