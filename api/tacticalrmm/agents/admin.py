from django.contrib import admin

from .models import Agent, AgentCustomField, Note, AgentHistory

admin.site.register(Agent)
admin.site.register(Note)
admin.site.register(AgentCustomField)
admin.site.register(AgentHistory)
