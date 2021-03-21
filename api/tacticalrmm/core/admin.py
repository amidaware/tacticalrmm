from django.contrib import admin

from .models import CoreSettings, CustomField

admin.site.register(CoreSettings)
admin.site.register(CustomField)
