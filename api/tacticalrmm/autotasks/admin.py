from django.contrib import admin

from .models import AutomatedTask, PolicyTaskResult

admin.site.register(AutomatedTask)
admin.site.register(PolicyTaskResult)