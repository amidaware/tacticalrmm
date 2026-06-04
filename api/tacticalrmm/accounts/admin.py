from django.contrib import admin
from rest_framework.authtoken.admin import TokenAdmin

from .models import Role, SSHPublicKey, SSHSession, User

admin.site.register(User)
TokenAdmin.raw_id_fields = ("user",)
admin.site.register(Role)
admin.site.register(SSHPublicKey)
admin.site.register(SSHSession)
