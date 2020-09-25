from django.contrib import admin

from .models import Agent, AgentOutage, RecoveryAction, Note

admin.site.register(Agent)
admin.site.register(AgentOutage)
admin.site.register(RecoveryAction)
admin.site.register(Note)
