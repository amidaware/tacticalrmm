from django.contrib import admin

from .models import (
    DiskCheck,
    DiskCheckEmail,
    PingCheck,
    PingCheckEmail,
    CpuLoadCheck,
    CpuLoadCheckEmail,
    MemCheck,
    MemCheckEmail,
    WinServiceCheck,
    WinServiceCheckEmail,
    ScriptCheck,
    ScriptCheckEmail,
    Script,
)

admin.site.register(DiskCheck)
admin.site.register(DiskCheckEmail)
admin.site.register(PingCheck)
admin.site.register(PingCheckEmail)
admin.site.register(CpuLoadCheck)
admin.site.register(CpuLoadCheckEmail)
admin.site.register(MemCheck)
admin.site.register(MemCheckEmail)
admin.site.register(WinServiceCheck)
admin.site.register(WinServiceCheckEmail)
admin.site.register(ScriptCheck)
admin.site.register(ScriptCheckEmail)
admin.site.register(Script)
