from django.contrib import admin

from .models import CodeSignToken, CoreSettings, CustomField

admin.site.register(CoreSettings)
admin.site.register(CustomField)
admin.site.register(CodeSignToken)
