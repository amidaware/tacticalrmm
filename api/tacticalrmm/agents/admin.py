from django.contrib import admin

from .models import Agent, AgentCustomField, Note, RecoveryAction

admin.site.register(Agent)
admin.site.register(RecoveryAction)
admin.site.register(Note)
admin.site.register(AgentCustomField)
