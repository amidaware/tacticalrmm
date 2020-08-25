from django.contrib import admin

from .models import Agent, AgentOutage, RecoveryAction

admin.site.register(Agent)
admin.site.register(AgentOutage)
admin.site.register(RecoveryAction)
