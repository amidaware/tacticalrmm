from django.contrib import admin

from .models import Agent, AgentCustomField, Note, RecoveryAction, AgentHistory

admin.site.register(Agent)
admin.site.register(RecoveryAction)
admin.site.register(Note)
admin.site.register(AgentCustomField)
admin.site.register(AgentHistory)
