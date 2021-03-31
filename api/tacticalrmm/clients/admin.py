from django.contrib import admin

from .models import Client, ClientCustomField, Deployment, Site, SiteCustomField

admin.site.register(Client)
admin.site.register(Site)
admin.site.register(Deployment)
admin.site.register(ClientCustomField)
admin.site.register(SiteCustomField)
