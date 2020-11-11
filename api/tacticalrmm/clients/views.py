import pytz
import re
import os
import uuid
import subprocess
import datetime as dt

from django.utils import timezone as djangotime
from django.db import DataError
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import HttpResponse

from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny


from rest_framework.decorators import api_view

from .serializers import (
    ClientSerializer,
    SiteSerializer,
    ClientTreeSerializer,
    DeploymentSerializer,
)
from .models import Client, Site, Deployment
from agents.models import Agent
from core.models import CoreSettings
from tacticalrmm.utils import notify_error


class GetAddClients(APIView):
    def get(self, request):
        clients = Client.objects.all()
        return Response(ClientSerializer(clients, many=True).data)

    def post(self, request):

        if "initialsetup" in request.data:
            client = {"name": request.data["client"]["client"].strip()}
            site = {"name": request.data["client"]["site"].strip()}
            serializer = ClientSerializer(data=client, context=request.data["client"])
            serializer.is_valid(raise_exception=True)
            core = CoreSettings.objects.first()
            core.default_time_zone = request.data["timezone"]
            core.save(update_fields=["default_time_zone"])
        else:
            client = {"name": request.data["client"].strip()}
            site = {"name": request.data["site"].strip()}
            serializer = ClientSerializer(data=client, context=request.data)
            serializer.is_valid(raise_exception=True)

        obj = serializer.save()
        Site(client=obj, name=site["name"]).save()

        return Response(f"{obj} was added!")


class GetUpdateDeleteClient(APIView):
    def put(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        serializer = ClientSerializer(data=request.data, instance=client)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("The Client was renamed")

    def delete(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        agent_count = Agent.objects.filter(site__client=client).count()
        if agent_count > 0:
            return notify_error(
                f"Cannot delete {client} while {agent_count} agents exist in it. Move the agents to another client first."
            )

        client.delete()
        return Response(f"{client.name} was deleted!")


class GetClientTree(APIView):
    def get(self, request):
        clients = Client.objects.all()
        return Response(ClientTreeSerializer(clients, many=True).data)


class GetAddSites(APIView):
    def get(self, request):
        sites = Site.objects.all()
        return Response(SiteSerializer(sites, many=True).data)

    def post(self, request):
        name = request.data["name"].strip()
        serializer = SiteSerializer(
            data={"name": name, "client": request.data["client"]},
            context={"clientpk": request.data["client"]},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")


class GetUpdateDeleteSite(APIView):
    def put(self, request, pk):

        site = get_object_or_404(Site, pk=pk)
        serializer = SiteSerializer(instance=site, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    def delete(self, request, pk):
        site = get_object_or_404(Site, pk=pk)
        if site.client.sites.count() == 1:
            return notify_error(f"A client must have at least 1 site.")

        agent_count = Agent.objects.filter(site=site).count()

        if agent_count > 0:
            return notify_error(
                f"Cannot delete {site.name} while {agent_count} agents exist in it. Move the agents to another site first."
            )

        site.delete()
        return Response(f"{site.name} was deleted!")


class AgentDeployment(APIView):
    def get(self, request):
        deps = Deployment.objects.all()
        return Response(DeploymentSerializer(deps, many=True).data)

    def post(self, request):
        from knox.models import AuthToken

        client = get_object_or_404(Client, pk=request.data["client"])
        site = get_object_or_404(Site, pk=request.data["site"])

        expires = dt.datetime.strptime(
            request.data["expires"], "%Y-%m-%d %H:%M"
        ).astimezone(pytz.timezone("UTC"))
        now = djangotime.now()
        delta = expires - now
        obj, token = AuthToken.objects.create(user=request.user, expiry=delta)

        flags = {
            "power": request.data["power"],
            "ping": request.data["ping"],
            "rdp": request.data["rdp"],
        }

        Deployment(
            client=client,
            site=site,
            expiry=expires,
            mon_type=request.data["agenttype"],
            arch=request.data["arch"],
            auth_token=obj,
            token_key=token,
            install_flags=flags,
        ).save()
        return Response("ok")

    def delete(self, request, pk):
        d = get_object_or_404(Deployment, pk=pk)
        try:
            d.auth_token.delete()
        except:
            pass

        d.delete()
        return Response("ok")


class GenerateAgent(APIView):

    permission_classes = (AllowAny,)

    def get(self, request, uid):
        try:
            _ = uuid.UUID(uid, version=4)
        except ValueError:
            return notify_error("invalid")

        d = get_object_or_404(Deployment, uid=uid)

        go_bin = "/usr/local/rmmgo/go/bin/go"

        if not os.path.exists(go_bin):
            return notify_error("Missing golang")

        api = f"{request.scheme}://{request.get_host()}"
        inno = (
            f"winagent-v{settings.LATEST_AGENT_VER}.exe"
            if d.arch == "64"
            else f"winagent-v{settings.LATEST_AGENT_VER}-x86.exe"
        )
        download_url = settings.DL_64 if d.arch == "64" else settings.DL_32

        client = d.client.name.replace(" ", "").lower()
        site = d.site.name.replace(" ", "").lower()
        client = re.sub(r"([^a-zA-Z0-9]+)", "", client)
        site = re.sub(r"([^a-zA-Z0-9]+)", "", site)

        ext = ".exe" if d.arch == "64" else "-x86.exe"

        file_name = f"rmm-{client}-{site}-{d.mon_type}{ext}"
        exe = os.path.join(settings.EXE_DIR, file_name)

        if os.path.exists(exe):
            try:
                os.remove(exe)
            except:
                pass

        goarch = "amd64" if d.arch == "64" else "386"
        cmd = [
            "env",
            "GOOS=windows",
            f"GOARCH={goarch}",
            go_bin,
            "build",
            f"-ldflags=\"-X 'main.Inno={inno}'",
            f"-X 'main.Api={api}'",
            f"-X 'main.Client={d.client.pk}'",
            f"-X 'main.Site={d.site.pk}'",
            f"-X 'main.Atype={d.mon_type}'",
            f"-X 'main.Rdp={d.install_flags['rdp']}'",
            f"-X 'main.Ping={d.install_flags['ping']}'",
            f"-X 'main.Power={d.install_flags['power']}'",
            f"-X 'main.DownloadUrl={download_url}'",
            f"-X 'main.Token={d.token_key}'\"",
            "-o",
            exe,
        ]

        gen = [
            "env",
            "GOOS=windows",
            f"GOARCH={goarch}",
            go_bin,
            "generate",
        ]
        try:
            r1 = subprocess.run(
                " ".join(gen),
                capture_output=True,
                shell=True,
                cwd=os.path.join(settings.BASE_DIR, "core/goinstaller"),
            )
        except:
            return notify_error("genfailed")

        if r1.returncode != 0:
            return notify_error("genfailed")

        try:
            r = subprocess.run(
                " ".join(cmd),
                capture_output=True,
                shell=True,
                cwd=os.path.join(settings.BASE_DIR, "core/goinstaller"),
            )
        except:
            return notify_error("buildfailed")

        if r.returncode != 0:
            return notify_error("buildfailed")

        if settings.DEBUG:
            with open(exe, "rb") as f:
                response = HttpResponse(
                    f.read(),
                    content_type="application/vnd.microsoft.portable-executable",
                )
                response["Content-Disposition"] = f"inline; filename={file_name}"
                return response
        else:
            response = HttpResponse()
            response["Content-Disposition"] = f"attachment; filename={file_name}"
            response["X-Accel-Redirect"] = f"/private/exe/{file_name}"
            return response