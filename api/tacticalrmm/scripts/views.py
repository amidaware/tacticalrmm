import base64

from django.conf import settings
from django.shortcuts import get_object_or_404
from loguru import logger
from rest_framework.decorators import api_view
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView

from tacticalrmm.utils import notify_error

from .models import Script
from .serializers import ScriptSerializer, ScriptTableSerializer

logger.configure(**settings.LOG_CONFIG)


class GetAddScripts(APIView):
    parser_class = (FileUploadParser,)

    def get(self, request):
        scripts = Script.objects.all()
        return Response(ScriptTableSerializer(scripts, many=True).data)

    def post(self, request, format=None):

        data = {
            "name": request.data["name"],
            "category": request.data["category"],
            "description": request.data["description"],
            "shell": request.data["shell"],
            "default_timeout": request.data["default_timeout"],
            "args": request.data["args"].split(",") if request.data["args"] else [],
            "script_type": "userdefined",  # force all uploads to be userdefined. built in scripts cannot be edited by user
        }

        if "favorite" in request.data:
            data["favorite"] = request.data["favorite"]

        if "filename" in request.data:
            message_bytes = request.data["filename"].read()
            data["code_base64"] = base64.b64encode(message_bytes).decode(
                "ascii", "ignore"
            )

        elif "code" in request.data:
            message_bytes = request.data["code"].encode("ascii", "ignore")
            data["code_base64"] = base64.b64encode(message_bytes).decode("ascii")

        serializer = ScriptSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        return Response(f"{obj.name} was added!")


class GetUpdateDeleteScript(APIView):
    def get(self, request, pk):
        script = get_object_or_404(Script, pk=pk)
        return Response(ScriptSerializer(script).data)

    def put(self, request, pk):
        script = get_object_or_404(Script, pk=pk)

        data = request.data

        if script.script_type == "builtin":
            # allow only favoriting builtin scripts
            if "favorite" in data:
                # overwrite request data
                data = {"favorite": data["favorite"]}
            else:
                return notify_error("Community scripts cannot be edited.")

        elif "code" in data:
            message_bytes = data["code"].encode("ascii")
            data["code_base64"] = base64.b64encode(message_bytes).decode("ascii")
            data.pop("code")

        serializer = ScriptSerializer(data=data, instance=script, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        return Response(f"{obj.name} was edited!")

    def delete(self, request, pk):
        script = get_object_or_404(Script, pk=pk)

        # this will never trigger but check anyway
        if script.script_type == "builtin":
            return notify_error("Community scripts cannot be deleted")

        script.delete()
        return Response(f"{script.name} was deleted!")


@api_view()
def download(request, pk):
    script = get_object_or_404(Script, pk=pk)

    if script.shell == "powershell":
        filename = f"{script.name}.ps1"
    elif script.shell == "cmd":
        filename = f"{script.name}.bat"
    else:
        filename = f"{script.name}.py"

    return Response({"filename": filename, "code": script.code})
