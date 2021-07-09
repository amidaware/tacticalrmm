import base64
import json
import asyncio

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from tacticalrmm.utils import notify_error

from .models import Script
from .permissions import ManageScriptsPerms
from .serializers import ScriptSerializer, ScriptTableSerializer


class GetAddScripts(APIView):
    permission_classes = [IsAuthenticated, ManageScriptsPerms]
    parser_class = (FileUploadParser,)

    def get(self, request):

        showCommunityScripts = request.GET.get("showCommunityScripts", True)
        if not showCommunityScripts or showCommunityScripts == "false":
            scripts = Script.objects.filter(script_type="userdefined")
        else:
            scripts = Script.objects.all()

        return Response(ScriptTableSerializer(scripts, many=True).data)

    def post(self, request, format=None):
        data = {
            "name": request.data["name"],
            "category": request.data["category"],
            "description": request.data["description"],
            "shell": request.data["shell"],
            "default_timeout": request.data["default_timeout"],
            "script_type": "userdefined",  # force all uploads to be userdefined. built in scripts cannot be edited by user
        }

        # code editor upload
        if "args" in request.data.keys() and isinstance(request.data["args"], list):
            data["args"] = request.data["args"]

        # file upload, have to json load it cuz it's formData
        if "args" in request.data.keys() and "file_upload" in request.data.keys():
            data["args"] = json.loads(request.data["args"])  # type: ignore

        if "favorite" in request.data.keys():
            data["favorite"] = request.data["favorite"]

        if "filename" in request.data.keys():
            message_bytes = request.data["filename"].read()
            data["code_base64"] = base64.b64encode(message_bytes).decode(
                "ascii", "ignore"
            )

        elif "code" in request.data.keys():
            message_bytes = request.data["code"].encode("ascii", "ignore")
            data["code_base64"] = base64.b64encode(message_bytes).decode("ascii")

        serializer = ScriptSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        return Response(f"{obj.name} was added!")


class GetUpdateDeleteScript(APIView):
    permission_classes = [IsAuthenticated, ManageScriptsPerms]

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


class TestScript(APIView):
    def post(self, request):
        from .models import Script
        from agents.models import Agent

        agent = get_object_or_404(Agent, pk=request.data["agent"])

        parsed_args = Script.parse_script_args(
            self, request.data["shell"], request.data["args"]
        )

        data = {
            "func": "runscript",
            "timeout": request.data["timeout"],
            "script_args": parsed_args,
            "payload": {
                "code": request.data["code"],
                "shell": request.data["shell"],
            },
        }

        r = asyncio.run(
            agent.nats_cmd(data, timeout=request.data["timeout"], wait=True)
        )

        return Response(r)


@api_view()
@permission_classes([IsAuthenticated, ManageScriptsPerms])
def download(request, pk):
    script = get_object_or_404(Script, pk=pk)

    if script.shell == "powershell":
        filename = f"{script.name}.ps1"
    elif script.shell == "cmd":
        filename = f"{script.name}.bat"
    else:
        filename = f"{script.name}.py"

    return Response({"filename": filename, "code": script.code})
