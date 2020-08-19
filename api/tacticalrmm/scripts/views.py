import os
from loguru import logger

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import HttpResponse

from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser

from .models import Script
from .serializers import ScriptSerializer
from tacticalrmm.utils import notify_error

logger.configure(**settings.LOG_CONFIG)


class GetAddScripts(APIView):
    parser_class = (FileUploadParser,)

    def get(self, request):
        scripts = Script.objects.all()
        return Response(ScriptSerializer(scripts, many=True).data)

    def put(self, request, format=None):

        file_obj = request.data["filename"]  # the actual file in_memory object

        # need to manually create the serialized data
        # since javascript formData doesn't support JSON
        filename = str(file_obj)
        data = {
            "name": request.data["name"],
            "filename": filename,
            "description": request.data["description"],
            "shell": request.data["shell"],
            "script_type": "userdefined",  # force all uploads to be userdefined. built in scripts cannot be edited by user
        }

        serializer = ScriptSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        with open(obj.file, "wb+") as f:
            for chunk in file_obj.chunks():
                f.write(chunk)

        return Response(f"{obj.name} was added!")


class GetUpdateDeleteScript(APIView):
    parser_class = (FileUploadParser,)

    def get(self, request, pk):
        script = get_object_or_404(Script, pk=pk)
        return Response(ScriptSerializer(script).data)

    def put(self, request, pk, format=None):
        script = get_object_or_404(Script, pk=pk)

        # this will never trigger but check anyway
        if script.script_type == "builtin":
            return notify_error("Built in scripts cannot be edited")

        data = {
            "name": request.data["name"],
            "description": request.data["description"],
            "shell": request.data["shell"],
        }

        # if uploading a new version of the script
        if "filename" in request.data:
            file_obj = request.data["filename"]
            data["filename"] = str(file_obj)

        serializer = ScriptSerializer(data=data, instance=script, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        if "filename" in request.data:

            try:
                os.remove(obj.file)
            except OSError:
                pass

            with open(obj.file, "wb+") as f:
                for chunk in file_obj.chunks():
                    f.write(chunk)

        return Response(f"{obj.name} was edited!")

    def delete(self, request, pk):
        script = get_object_or_404(Script, pk=pk)

        # this will never trigger but check anyway
        if script.script_type == "builtin":
            return notify_error("Built in scripts cannot be deleted")

        try:
            os.remove(script.file)
        except OSError:
            pass

        script.delete()
        return Response(f"{script.name} was deleted!")


@api_view()
def download(request, pk):
    script = get_object_or_404(Script, pk=pk)
    use_nginx = False
    conf = "/etc/nginx/sites-available/rmm.conf"

    if os.path.exists(conf):
        try:
            with open(conf) as f:
                for line in f.readlines():
                    if "location" and "builtin" in line:
                        use_nginx = True
                        break
        except Exception as e:
            logger.error(e)
    else:
        use_nginx = True

    if settings.DEBUG or not use_nginx:
        with open(script.file, "rb") as f:
            response = HttpResponse(f.read(), content_type="text/plain")
            response["Content-Disposition"] = f"attachment; filename={script.filename}"
            return response
    else:
        response = HttpResponse()
        response["Content-Disposition"] = f"attachment; filename={script.filename}"

        response["X-Accel-Redirect"] = (
            f"/saltscripts/{script.filename}"
            if script.script_type == "userdefined"
            else f"/builtin/{script.filename}"
        )
        return response
