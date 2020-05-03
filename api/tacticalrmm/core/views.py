from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import CoreSettings
from .serializers import CoreSettingsSerializer


@api_view()
def get_core_settings(request):
    settings = CoreSettings.objects.first()
    return Response(CoreSettingsSerializer(settings).data)


@api_view(["PATCH"])
def edit_settings(request):
    settings = CoreSettings.objects.first()
    serializer = CoreSettingsSerializer(instance=settings, data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response("ok")
