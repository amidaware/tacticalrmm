from django.contrib import admin

from .models import AuditLog, PendingAction

admin.site.register(PendingAction)
admin.site.register(AuditLog)
