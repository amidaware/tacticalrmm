from django.contrib import admin

from .models import Policy, PolicyExclusions

admin.site.register(Policy)
admin.site.register(PolicyExclusions)
