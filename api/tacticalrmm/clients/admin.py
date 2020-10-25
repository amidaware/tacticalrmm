from django.contrib import admin

from .models import Client, Site, Deployment

admin.site.register(Client)
admin.site.register(Site)
admin.site.register(Deployment)
