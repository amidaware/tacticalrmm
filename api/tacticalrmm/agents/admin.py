from django.contrib import admin

from .models import Agent, RecoveryAction, Note

admin.site.register(Agent)
admin.site.register(RecoveryAction)
admin.site.register(Note)
