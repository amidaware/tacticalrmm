import asyncio

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.permissions import RunScriptPerms
from tacticalrmm.constants import ScriptShell, ScriptType
from tacticalrmm.helpers import notify_error

from .models import Script, ScriptSnippet
from .permissions import ScriptsPerms
from .serializers import (
    ScriptSerializer,
    ScriptSnippetSerializer,
    ScriptTableSerializer,
)


class GetAddScripts(APIView):
    permission_classes = [IsAuthenticated, ScriptsPerms]

    def get(self, request):

        showCommunityScripts = request.GET.get("showCommunityScripts", True)
        showHiddenScripts = request.GET.get("showHiddenScripts", False)

        if not showCommunityScripts or showCommunityScripts == "false":
            scripts = Script.objects.filter(script_type=ScriptType.USER_DEFINED)
        else:
            scripts = Script.objects.all()

        if not showHiddenScripts or showHiddenScripts != "true":
            scripts = scripts.filter(hidden=False)

        return Response(
            ScriptTableSerializer(scripts.order_by("category"), many=True).data
        )

    def post(self, request):

        serializer = ScriptSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        # obj.hash_script_body()

        return Response(f"{obj.name} was added!")


class GetUpdateDeleteScript(APIView):
    permission_classes = [IsAuthenticated, ScriptsPerms]

    def get(self, request, pk):
        script = get_object_or_404(Script, pk=pk)
        return Response(ScriptSerializer(script).data)

    def put(self, request, pk):
        script = get_object_or_404(Script, pk=pk)

        data = request.data

        if script.script_type == ScriptType.BUILT_IN:
            # allow only favoriting builtin scripts
            if "favorite" in data:
                # overwrite request data
                data = {"favorite": data["favorite"]}
            elif "hidden" in data:
                data = {"hidden": data["hidden"]}
            else:
                return notify_error("Community scripts cannot be edited.")

        serializer = ScriptSerializer(data=data, instance=script, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        # obj.hash_script_body()

        return Response(f"{obj.name} was edited!")

    def delete(self, request, pk):
        script = get_object_or_404(Script, pk=pk)

        # this will never trigger but check anyway
        if script.script_type == ScriptType.BUILT_IN:
            return notify_error("Community scripts cannot be deleted")

        script.delete()
        return Response(f"{script.name} was deleted!")


class GetAddScriptSnippets(APIView):
    permission_classes = [IsAuthenticated, ScriptsPerms]

    def get(self, request):
        snippets = ScriptSnippet.objects.all()
        return Response(ScriptSnippetSerializer(snippets, many=True).data)

    def post(self, request):

        serializer = ScriptSnippetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("Script snippet was saved successfully")


class GetUpdateDeleteScriptSnippet(APIView):
    permission_classes = [IsAuthenticated, ScriptsPerms]

    def get(self, request, pk):
        snippet = get_object_or_404(ScriptSnippet, pk=pk)
        return Response(ScriptSnippetSerializer(snippet).data)

    def put(self, request, pk):
        snippet = get_object_or_404(ScriptSnippet, pk=pk)

        serializer = ScriptSnippetSerializer(
            instance=snippet, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("Script snippet was saved successfully")

    def delete(self, request, pk):
        snippet = get_object_or_404(ScriptSnippet, pk=pk)
        snippet.delete()

        return Response("Script snippet was deleted successfully")


class TestScript(APIView):
    permission_classes = [IsAuthenticated, RunScriptPerms]

    def post(self, request, agent_id):
        from agents.models import Agent

        from .models import Script

        agent = get_object_or_404(Agent, agent_id=agent_id)

        parsed_args = Script.parse_script_args(
            agent, request.data["shell"], request.data["args"]
        )

        data = {
            "func": "runscript",
            "timeout": request.data["timeout"],
            "script_args": parsed_args,
            "payload": {
                "code": Script.replace_with_snippets(request.data["code"]),
                "shell": request.data["shell"],
            },
        }

        r = asyncio.run(
            agent.nats_cmd(data, timeout=request.data["timeout"], wait=True)
        )

        return Response(r)


@api_view(["GET"])
@permission_classes([IsAuthenticated, ScriptsPerms])
def download(request, pk):
    script = get_object_or_404(Script, pk=pk)

    with_snippets = request.GET.get("with_snippets", True)

    if with_snippets == "false":
        with_snippets = False

    match script.shell:
        case ScriptShell.POWERSHELL:
            ext = ".ps1"
        case ScriptShell.CMD:
            ext = ".bat"
        case ScriptShell.PYTHON:
            ext = ".py"
        case ScriptShell.SHELL:
            ext = ".sh"
        case _:
            ext = ""

    return Response(
        {
            "filename": f"{script.name}{ext}",
            "code": script.code if with_snippets else script.code_no_snippets,
        }
    )
