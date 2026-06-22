from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from clients.models import Site
from logs.models import AuditLog
from tacticalrmm.helpers import notify_error
from tacticalrmm.permissions import _has_perm_on_site

from .models import NetworkDevice
from .permissions import NetDeviceConnectPerms, NetDevicePerms
from .serializers import NetworkDeviceSerializer


class GetAddNetworkDevices(APIView):
    permission_classes = [IsAuthenticated, NetDevicePerms]

    def get(self, request):
        allowed_sites = Site.objects.filter_by_role(request.user)
        devices = NetworkDevice.objects.select_related("site__client").filter(
            site__in=allowed_sites
        )

        site = request.query_params.get("site")
        client = request.query_params.get("client")
        if site:
            devices = devices.filter(site_id=site)
        elif client:
            devices = devices.filter(site__client_id=client)

        return Response(NetworkDeviceSerializer(devices, many=True).data)

    def post(self, request):
        site_id = request.data.get("site")
        if not site_id or not _has_perm_on_site(request.user, site_id):
            return notify_error("You do not have permission to this site")

        serializer = NetworkDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = serializer.save()

        AuditLog.objects.create(
            username=request.user.username,
            object_type="netdevice",
            action="add",
            message=f"{request.user.username} added network device {device.name}",
            after_value=NetworkDeviceSerializer(device).data,
        )
        return Response(NetworkDeviceSerializer(device).data)


class GetUpdateDeleteNetworkDevice(APIView):
    permission_classes = [IsAuthenticated, NetDevicePerms]

    def _get(self, pk):
        return get_object_or_404(
            NetworkDevice.objects.select_related("site__client"), pk=pk
        )

    def get(self, request, pk):
        device = self._get(pk)
        if not _has_perm_on_site(request.user, device.site_id):
            return notify_error("Permission denied")
        return Response(NetworkDeviceSerializer(device).data)

    def put(self, request, pk):
        device = self._get(pk)
        if not _has_perm_on_site(request.user, device.site_id):
            return notify_error("Permission denied")
        # if site is being changed, verify access to the target site too
        new_site = request.data.get("site")
        if new_site and int(new_site) != device.site_id:
            if not _has_perm_on_site(request.user, new_site):
                return notify_error("Permission denied for target site")

        serializer = NetworkDeviceSerializer(
            instance=device, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        device = serializer.save()
        return Response(NetworkDeviceSerializer(device).data)

    def delete(self, request, pk):
        device = self._get(pk)
        if not _has_perm_on_site(request.user, device.site_id):
            return notify_error("Permission denied")
        name = device.name
        device.delete()
        AuditLog.objects.create(
            username=request.user.username,
            object_type="netdevice",
            action="delete",
            message=f"{request.user.username} deleted network device {name}",
        )
        return Response(f"{name} was deleted")


class NetworkDeviceConnect(APIView):
    permission_classes = [IsAuthenticated, NetDeviceConnectPerms]

    def post(self, request, pk):
        device = get_object_or_404(
            NetworkDevice.objects.select_related("site__client"), pk=pk
        )
        if not _has_perm_on_site(request.user, device.site_id):
            return notify_error("Permission denied")

        # try preferred agents in order and verify each can actually reach the
        # device, falling back to the next one if not
        agent, tried = device.resolve_reachable_agent()
        if not agent:
            return notify_error(
                "No online agent is available to reach this device. "
                "Check that a preferred agent (or an agent in the same site/client) is online."
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type="netdevice",
            action="remote_session",
            message=(
                f"{request.user.username} connected to network device "
                f"{device.name} ({device.protocol}://{device.ip_address}:{device.port}) "
                f"via {agent.hostname}"
            ),
        )

        return Response(
            {
                "agent_id": agent.agent_id,
                "agent_hostname": agent.hostname,
                "protocol": device.protocol,
                "address": device.ip_address,
                "port": device.port,
                "name": device.name,
            }
        )
