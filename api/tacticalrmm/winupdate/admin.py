from django.contrib import admin

from .models import WinUpdate, WinUpdatePolicy

admin.site.register(WinUpdate)
admin.site.register(WinUpdatePolicy)
