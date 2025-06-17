from django.contrib import admin

from .models import CodeSignToken, CoreSettings, CustomField, Schedule

admin.site.register(CoreSettings)
admin.site.register(CustomField)
admin.site.register(CodeSignToken)
admin.site.register(Schedule)
