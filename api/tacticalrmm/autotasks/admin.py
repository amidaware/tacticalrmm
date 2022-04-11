from django.contrib import admin

from .models import AutomatedTask, TaskResult

admin.site.register(AutomatedTask)
admin.site.register(TaskResult)
