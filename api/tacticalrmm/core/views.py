import subprocess

from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.response import Response
from rest_framework import status

from .models import CoreSettings
from .serializers import CoreSettingsSerializer


@api_view()
def get_core_settings(request):
    settings = CoreSettings.objects.all().get()
    return Response(CoreSettingsSerializer(settings).data)


@api_view(["PATCH"])
def edit_settings(request):
    settings = CoreSettings.objects.all().get()
    serializer = CoreSettingsSerializer(instance=settings, data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    try:
        r = subprocess.run(["sudo", "systemctl", "restart", "celerybeat.service"])
    except Exception:
        return Response("error", status=status.HTTP_400_BAD_REQUEST)

    if r.returncode != 0:
        return Response("error", status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response("ok")

    return Response("ok")
