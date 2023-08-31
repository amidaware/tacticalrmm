from django.contrib import admin

from .models import Agent, AgentCustomField, AgentHistory, Note

admin.site.register(Agent)
admin.site.register(Note)
admin.site.register(AgentCustomField)
admin.site.register(AgentHistory)
