from django.contrib import admin

from .models import Policy, AutomatedTask

admin.site.register(Policy)
admin.site.register(AutomatedTask)
