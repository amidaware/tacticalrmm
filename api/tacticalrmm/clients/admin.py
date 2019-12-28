from django.contrib import admin

from .models import Client, Site

admin.site.register(Client)
admin.site.register(Site)
