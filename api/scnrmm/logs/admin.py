from django.contrib import admin

from .models import AuditLog, DebugLog, PendingAction

admin.site.register(PendingAction)
admin.site.register(AuditLog)
admin.site.register(DebugLog)
