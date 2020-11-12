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
from tacticalrmm.utils import notify_error
from automation.tasks import generate_all_agent_checks_task


class UploadMeshAgent(APIView):
    parser_class = (FileUploadParser,)

    def put(self, request, format=None):
        if "meshagent" not in request.data and "arch" not in request.data:
            raise ParseError("Empty content")

        arch = request.data["arch"]
        f = request.data["meshagent"]
        mesh_exe = os.path.join(
            settings.EXE_DIR, "meshagent.exe" if arch == "64" else "meshagent-x86.exe"
        )
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
    new_settings = serializer.save()

    # check if default policies changed
    if settings.server_policy != new_settings.server_policy:
        generate_all_agent_checks_task.delay(
            mon_type="server", clear=True, create_tasks=True
        )

    if settings.workstation_policy != new_settings.workstation_policy:
        generate_all_agent_checks_task.delay(
            mon_type="workstation", clear=True, create_tasks=True
        )

    return Response("ok")


@api_view()
def version(request):
    return Response(settings.APP_VER)


@api_view()
def dashboard_info(request):
    return Response(
        {"trmm_version": settings.TRMM_VERSION, "dark_mode": request.user.dark_mode}
    )


@api_view()
def email_test(request):
    core = CoreSettings.objects.first()
    r = core.send_mail(
        subject="Test from Tactical RMM", body="This is a test message", test=True
    )

    if not isinstance(r, bool) and isinstance(r, str):
        return notify_error(r)

    return Response("Email Test OK!")
