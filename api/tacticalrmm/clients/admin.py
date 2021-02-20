from django.contrib import admin

from .models import Client, Deployment, Site

admin.site.register(Client)
admin.site.register(Site)
admin.site.register(Deployment)
