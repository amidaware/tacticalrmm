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
    TreeSerializer,
    DeploymentSerializer,
)
from .models import Client, Site, Deployment, validate_name
from agents.models import Agent
from core.models import CoreSettings
from tacticalrmm.utils import notify_error


class GetAddClients(APIView):
    def get(self, request):
        clients = Client.objects.all()
        return Response(ClientSerializer(clients, many=True).data)

    def post(self, request):

        if "initialsetup" in request.data:
            client = {"client": request.data["client"]["client"].strip()}
            site = {"site": request.data["client"]["site"].strip()}
            serializer = ClientSerializer(data=client, context=request.data["client"])
            serializer.is_valid(raise_exception=True)
            core = CoreSettings.objects.first()
            core.default_time_zone = request.data["timezone"]
            core.save(update_fields=["default_time_zone"])
        else:
            client = {"client": request.data["client"].strip()}
            site = {"site": request.data["site"].strip()}
            serializer = ClientSerializer(data=client, context=request.data)
            serializer.is_valid(raise_exception=True)

        obj = serializer.save()
        Site(client=obj, site=site["site"]).save()

        return Response(f"{obj} was added!")


class GetUpdateDeleteClient(APIView):
    def patch(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        orig = client.client

        serializer = ClientSerializer(data=request.data, instance=client)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()

        agents = Agent.objects.filter(client=orig)
        for agent in agents:
            agent.client = obj.client
            agent.save(update_fields=["client"])

        return Response(f"{orig} renamed to {obj}")

    def delete(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        agents = Agent.objects.filter(client=client.client)
        if agents.exists():
            return notify_error(
                f"Cannot delete {client} while {agents.count()} agents exist in it. Move the agents to another client first."
            )

        client.delete()
        return Response(f"{client.client} was deleted!")


class GetAddSites(APIView):
    def get(self, request):
        sites = Site.objects.all()
        return Response(SiteSerializer(sites, many=True).data)


@api_view(["POST"])
def add_site(request):
    client = Client.objects.get(client=request.data["client"].strip())
    site = request.data["site"].strip()

    if not validate_name(site):
        content = {"error": "Site name cannot contain the | character"}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

    if Site.objects.filter(client=client).filter(site=site):
        content = {"error": f"Site {site} already exists"}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

    try:
        Site(client=client, site=site).save()
    except DataError:
        content = {"error": "Site name too long (max 255 chars)"}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response("ok")


@api_view(["PATCH"])
def edit_site(request):
    new_name = request.data["name"].strip()

    if not validate_name(new_name):
        err = "Site name cannot contain the | character"
        return Response(err, status=status.HTTP_400_BAD_REQUEST)

    client = get_object_or_404(Client, client=request.data["client"])
    site = Site.objects.filter(client=client).filter(site=request.data["site"]).get()

    agents = Agent.objects.filter(client=client.client).filter(site=site.site)

    site.site = new_name
    site.save(update_fields=["site"])

    for agent in agents:
        agent.site = new_name
        agent.save(update_fields=["site"])

    return Response("ok")


@api_view(["DELETE"])
def delete_site(request):
    client = get_object_or_404(Client, client=request.data["client"])
    if client.sites.count() == 1:
        return notify_error(f"A client must have at least 1 site.")

    site = Site.objects.filter(client=client).filter(site=request.data["site"]).get()
    agents = Agent.objects.filter(client=client.client).filter(site=site.site)

    if agents.exists():
        return notify_error(
            f"Cannot delete {site} while {agents.count()} agents exist in it. Move the agents to another site first."
        )

    site.delete()
    return Response(f"{site} was deleted!")


@api_view()
# for vue
def list_clients(request):
    clients = Client.objects.all()
    return Response(ClientSerializer(clients, many=True).data)


@api_view()
# for vue
def list_sites(request):
    sites = Site.objects.all()
    return Response(TreeSerializer(sites, many=True).data)


@api_view()
def load_tree(request):
    clients = Client.objects.all()
    new = {}

    for x in clients:
        b = []

        sites = Site.objects.filter(client=x)
        for i in sites:

            if i.has_maintenanace_mode_agents:
                b.append(f"{i.site}|{i.pk}|warning")
            elif i.has_failing_checks:
                b.append(f"{i.site}|{i.pk}|negative")
            else:
                b.append(f"{i.site}|{i.pk}|black")
                
            if i.has_maintenanace_mode_agents:
                new[f"{x.client}|{x.pk}|warning"] = b
            elif x.has_failing_checks:
                new[f"{x.client}|{x.pk}|negative"] = b
            else:
                new[f"{x.client}|{x.pk}|black"] = b

    return Response(new)


@api_view()
def load_clients(request):
    clients = Client.objects.all()
    new = {}

    for x in clients:
        b = []

        sites = Site.objects.filter(client=x)
        for i in sites:
            b.append(i.site)
            new[x.client] = b

    return Response(new)


class AgentDeployment(APIView):
    def get(self, request):
        deps = Deployment.objects.all()
        return Response(DeploymentSerializer(deps, many=True).data)

    def post(self, request):
        from knox.models import AuthToken

        client = get_object_or_404(Client, client=request.data["client"])
        site = get_object_or_404(Site, client=client, site=request.data["site"])

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

        client = d.client.client.replace(" ", "").lower()
        site = d.site.site.replace(" ", "").lower()
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