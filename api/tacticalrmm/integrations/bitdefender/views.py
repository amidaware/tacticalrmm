from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
import requests
import json
from ..models import Integration
import base64

class GetEndpoints(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")

        json = {
            "params": {
                "perPage": 100,
                "page": int(request.query_params['pageNumber']),
                "filters": {
                    "type": {"computers": True, "virtualMachines": True},
                    "security": {"management": {"managedWithBest": True}},
                    "depth": {"allItemsRecursively": True},
                },
            },
            "jsonrpc": "2.0",
            "method": "getNetworkInventoryItems",
            "id": integration.company_id,
        }
        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/network",
            json=json,
            verify=False,
            headers={
                "Content-Type": "application/json",
                "Authorization": integration.auth_header,
            },
        ).json()

        return Response(result)


class GetEndpoint(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, endpoint_id, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")

        json = {
            "params": {
                "endpointId" : endpoint_id
                },
            "jsonrpc": "2.0",
            "method": "getManagedEndpointDetails",
            "id": integration.company_id,
        }
        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/network",
            json=json,
            verify=False,
            headers={
                "Content-Type": "application/json",
                "Authorization": integration.auth_header,
            },
        ).json()

        return Response(result)



class GetQuickScan(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, endpoint_id, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")

        endpoint_array = []
        endpoint_array.append(endpoint_id)

        json = {
                "params": {
                    "targetIds": endpoint_array,
                    "type": 1,
                    "name": "Tactical RMM initiated Quick Scan",
                },
                "jsonrpc": "2.0",
                "method": "createScanTask",
                "id": integration.company_id,
                }

        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/network",
            json=json,
            verify=False,
            headers={
                "Content-Type": "application/json",
                "Authorization": integration.auth_header,
            },
        ).json()

        return Response(result)

class GetFullScan(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, endpoint_id, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")

        endpoint_array = []
        endpoint_array.append(endpoint_id)
        
        json = {
                "params": {
                    "targetIds": endpoint_array,
                    "type": 2,
                    "name": "Tactical RMM initiated Full Scan",
                },
                "jsonrpc": "2.0",
                "method": "createScanTask",
                "id": integration.company_id,
                }

        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/network",
            json=json,
            verify=False,
            headers={
                "Content-Type": "application/json",
                "Authorization": integration.auth_header,
            },
        ).json()

        return Response(result)


class GetQuarantine(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")
        json = {
                "params": {
                        "perPage": 100,
                    },
                "jsonrpc": "2.0",
                "method": "getQuarantineItemsList",
                "id": integration.company_id
              }

        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/quarantine/computers",
        json=json,
        verify=False,
        headers = {
        "Content-Type": "application/json",
        "Authorization": integration.auth_header
        }).json()

        return Response(result)

class GetEndpointQuarantine(APIView):

    permission_classes = [IsAuthenticated] 

    def get(self, request, endpoint_id, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")
        print(endpoint_id)
        json = {
            "params": {
                    "endpointId": endpoint_id,
                    "perPage": 100,
                },
                "jsonrpc": "2.0",
                "method": "getQuarantineItemsList",
                "id": integration.company_id
              }

        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/quarantine/computers",
        json=json,
        verify=False,
        headers = {
        "Content-Type": "application/json",
        "Authorization": integration.auth_header
        }).json()
        print(result)
        return Response(result)

class GetTasks(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")
        json = {  
                "params": {
                    "perPage": 100
                },
                "jsonrpc": "2.0",
                "method": "getScanTasksList",
                "id": integration.company_id
              }

        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/network",
        json=json,
        verify=False,
        headers = {
        "Content-Type": "application/json",
        "Authorization": integration.auth_header
        }).json()

        return Response(result)