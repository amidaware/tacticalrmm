import datetime as dt
import re
import uuid

import pytz
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from core.models import CoreSettings
from tacticalrmm.utils import generate_installer_exe, notify_error

from .models import Client, Deployment, Site
from .serializers import (
    ClientSerializer,
    ClientTreeSerializer,
    DeploymentSerializer,
    SiteSerializer,
)


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

        serializer = ClientSerializer(data=request.data, instance=client, partial=True)
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
        serializer = SiteSerializer(instance=site, data=request.data, partial=True)
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

        inno = (
            f"winagent-v{settings.LATEST_AGENT_VER}.exe"
            if d.arch == "64"
            else f"winagent-v{settings.LATEST_AGENT_VER}-x86.exe"
        )
        client = d.client.name.replace(" ", "").lower()
        site = d.site.name.replace(" ", "").lower()
        client = re.sub(r"([^a-zA-Z0-9]+)", "", client)
        site = re.sub(r"([^a-zA-Z0-9]+)", "", site)
        ext = ".exe" if d.arch == "64" else "-x86.exe"

        return generate_installer_exe(
            file_name=f"rmm-{client}-{site}-{d.mon_type}{ext}",
            goarch="amd64" if d.arch == "64" else "386",
            inno=inno,
            api=f"https://{request.get_host()}",
            client_id=d.client.pk,
            site_id=d.site.pk,
            atype=d.mon_type,
            rdp=d.install_flags["rdp"],
            ping=d.install_flags["ping"],
            power=d.install_flags["power"],
            download_url=settings.DL_64 if d.arch == "64" else settings.DL_32,
            token=d.token_key,
        )
