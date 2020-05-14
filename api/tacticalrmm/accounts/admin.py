from django.contrib import admin

from rest_framework.authtoken.admin import TokenAdmin

from .models import User

admin.site.register(User)
TokenAdmin.raw_id_fields = ("user",)
