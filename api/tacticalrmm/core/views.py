import os

from django.conf import settings

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import FileUploadParser
from rest_framework.views import APIView

from .models import CoreSettings
from .serializers import CoreSettingsSerializer


class UploadMeshAgent(APIView):
    parser_class = (FileUploadParser,)

    def put(self, request, format=None):
        if "meshagent" not in request.data:
            raise ParseError("Empty content")

        f = request.data["meshagent"]
        mesh_exe = os.path.join(settings.EXE_DIR, "meshagent.exe")
        with open(mesh_exe, "wb+") as j:
            for chunk in f.chunks():
                j.write(chunk)

        return Response(status=status.HTTP_201_CREATED)


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
