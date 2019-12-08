from django.db import DataError

from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import (
    BasicAuthentication,
    TokenAuthentication,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from .serializers import ClientSerializer, SiteSerializer, TreeSerializer
from .models import Client, Site
from collections import defaultdict
from time import sleep

@api_view(["POST"])
def initial_setup(request):
    client_name = request.data["client"].strip()
    site_name = request.data["site"].strip()

    if "|" in client_name or "|" in site_name:
        err = {"error": f"Client/site name cannot contain the | character"}
        return Response(err, status=status.HTTP_400_BAD_REQUEST)
    
    Client(client=client_name).save()
    client = Client.objects.get(client=client_name)
    Site(client=client, site=site_name).save()
    return Response("ok")


@api_view(["POST"])
def add_client(request):
    # remove leading and trailing whitespaces
    client_name = request.data["client"].strip()
    default_site = request.data["site"].strip()

    if "|" in client_name:
        content = {"error": f"Client name cannot contain the | character"}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

    if Client.objects.filter(client=client_name):
        content = {"error": f"Client {client_name} already exists"}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

    try:
        Client(client=client_name).save()
    except DataError:
        content = {"error": "Client name too long (max 255 chars)"}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)
    else:
        client = Client.objects.get(client=client_name)
        Site(client=client, site=default_site).save()
        return Response("ok")

@api_view(["POST"])
def add_site(request):
    client = Client.objects.get(client=request.data["client"].strip())
    site = request.data["site"].strip()

    if "|" in site:
        content = {"error": f"Site name cannot contain the | character"}
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

@api_view()
@authentication_classes((BasicAuthentication,))
@permission_classes((IsAuthenticated,))
# for installer
def installer_list_clients(request):
    clients = Client.objects.all()
    return Response(ClientSerializer(clients, many=True).data)

@api_view()
# for vue
def list_clients(request):
    clients = Client.objects.all()
    return Response(ClientSerializer(clients, many=True).data)


@api_view()
def load_tree(request):
    clients = Client.objects.all()
    new = {}
    
    for x in clients:
        b = []
        
        sites = Site.objects.filter(client=x)
        for i in sites:

            if i.checks_failing:
                b.append(f"{i.site}|{i.pk}|red")
            else:
                b.append(f"{i.site}|{i.pk}|grey")
            
            if x.checks_failing:
                new[f"{x.client}|{x.pk}|red"] = b
            else:
                new[f"{x.client}|{x.pk}|grey"] = b

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

@api_view()
@authentication_classes((BasicAuthentication,))
@permission_classes((IsAuthenticated,))
# get list of clients and sites for the installer
def installer_list_sites(request, client):
    sites = Site.objects.filter(client__client=client)
    return Response(SiteSerializer(sites, many=True).data)