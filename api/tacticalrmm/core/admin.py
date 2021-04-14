from django.contrib import admin

from .models import CoreSettings, CustomField, CodeSignToken

admin.site.register(CoreSettings)
admin.site.register(CustomField)
admin.site.register(CodeSignToken)
