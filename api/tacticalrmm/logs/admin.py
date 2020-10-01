from django.contrib import admin

from .models import PendingAction, AuditLog

admin.site.register(PendingAction)
admin.site.register(AuditLog)
