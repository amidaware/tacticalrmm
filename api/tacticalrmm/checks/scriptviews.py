import os

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser
from rest_framework.views import APIView
from rest_framework import status

from rest_framework.decorators import api_view

from agents.models import Agent

# from .models import Script

# from .serializers import ScriptSerializer


class UploadScript(APIView):
    parser_class = (FileUploadParser,)

    def put(self, request, format=None):
        if "script" not in request.data:
            raise ParseError("Empty content")

        f = request.data["script"]
        filename = str(f)

        name = request.data["name"]
        desc = request.data["desc"]
        shell = request.data["shell"]

        if not Script.validate_filename(filename):
            return Response(
                "Please upload a file with correct extension (.bat, .py, .ps1)",
                status=status.HTTP_400_BAD_REQUEST,
            )

        script_path = os.path.join("/srv/salt/scripts/userdefined", filename)

        if os.path.exists(script_path):
            return Response(
                f"Filename {filename} already exists. Delete or edit the existing script first",
                status=status.HTTP_400_BAD_REQUEST,
            )

        with open(script_path, "wb+") as j:
            for chunk in f.chunks():
                j.write(chunk)

        Script(name=name, description=desc, filename=filename, shell=shell).save()

        return Response(f"asd", status=status.HTTP_201_CREATED)


@api_view()
def view_script_code(request, pk):
    script = get_object_or_404(Script, pk=pk)

    with open(script.file, "r") as f:
        text = f.read()

    return Response({"name": script.filename, "text": text})


@api_view(["DELETE"])
def delete_script(request):
    script = get_object_or_404(Script, pk=request.data["pk"])
    filename = script.filename

    try:
        os.remove(script.file)
    except OSError:
        pass

    script.delete()

    return Response(filename)


@api_view()
def get_script(request, pk):
    script = get_object_or_404(Script, pk=pk)
    return Response(ScriptSerializer(script).data)


@api_view()
def download_script(request, pk):
    script = get_object_or_404(Script, pk=pk)

    if settings.DEBUG:
        with open(script.file, "rb") as f:
            response = HttpResponse(f.read(), content_type="text/plain")
            response["Content-Disposition"] = f"attachment; filename={script.filename}"
            return response
    else:
        response = HttpResponse()
        response["Content-Disposition"] = f"attachment; filename={script.filename}"
        response["X-Accel-Redirect"] = f"/protectedscripts/{script.filename}"
        return response


class EditScript(APIView):
    parser_class = (FileUploadParser,)

    def put(self, request, format=None):

        script = get_object_or_404(Script, pk=request.data["pk"])
        name = request.data["name"]
        desc = request.data["desc"]
        shell = request.data["shell"]

        script.name = name
        script.description = desc
        script.shell = shell

        if "script" in request.data:
            # if uploading a new version of the script
            f = request.data["script"]
            filename = str(f)
            if not script.validate_filename(filename):
                return Response(
                    "Please upload a file with correct extension (.bat, .py, .ps1)",
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # delete the old file
            try:
                os.remove(script.file)
            except OSError:
                pass

            updated_path = os.path.join("/srv/salt/scripts/userdefined/", filename)
            with open(updated_path, "wb+") as j:
                for chunk in f.chunks():
                    j.write(chunk)

            script.filename = filename
            script.save(update_fields=["name", "description", "shell", "filename"])
        else:
            script.save(update_fields=["name", "description", "shell"])

        return Response(f"asd", status=status.HTTP_201_CREATED)
