from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from datetime import datetime
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

class GetPackages(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")

        json = {
            "jsonrpc": "2.0",
            "method": "getInstallationLinks",
            "id": integration.company_id,
        }
        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/packages",
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

class GetReportsList(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")
        json = {
            "params": {
                "perPage": 100,
            },
            "jsonrpc": "2.0",
            "method": "getReportsList",
            "id": integration.company_id
        }  

        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/reports",
        json=json,
        verify=False,
        headers = {
        "Content-Type": "application/json",
        "Authorization": integration.auth_header
        }).json()

        return Response(result)


class GetCreateReport(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, endpoint_id, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")

        report_recipients_array = []
        endpoint_array = []
        endpoint_array.append(endpoint_id)

        for recipient in request.data['reportRecipients']:
            report_recipients_array.append(recipient)

        json = {
                "params": {
                    "name": request.data['name'],
                    "type": request.data['type'],
                    "targetIds": endpoint_array,
                    "scheduledInfo": {},
                    "options": {},
                    "emailsList": report_recipients_array
                },
                "jsonrpc": "2.0",
                "method": "createReport",
                "id": integration.company_id
            } 

        params_scheduledInfo = json['params']['scheduledInfo']
        params_options = json['params']['options']

        if request.data['occurrence']:
            params_scheduledInfo['occurrence'] = request.data['occurrence']

        if request.data['interval']:
            params_scheduledInfo['interval'] = request.data['interval']

        if request.data['days']:
            params_scheduledInfo['days'] = request.data['days']

        if request.data['day']:
            params_scheduledInfo['day'] = request.data['day']

        if request.data['occurrence'] == 3 or request.data['occurrence'] == 4 or request.data['occurrence'] == 5:
            params_scheduledInfo['startHour'] = int(request.data['startHour'])

        if request.data['occurrence'] == 3 or request.data['occurrence'] == 4 or request.data['occurrence'] == 5:
            params_scheduledInfo['startMinute'] = int(request.data['startMinute'])

        if request.data['reportingInterval']:
            params_options['reportingInterval'] = request.data['reportingInterval']

        # print(json)

        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/reports",
        json=json,
        verify=False,
        headers = {
        "Content-Type": "application/json",
        "Authorization": integration.auth_header
        }).json()

        return Response(result)


class GetDeleteReport(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, report_id, format=None):
        integration = Integration.objects.get(name="Bitdefender GravityZone")

        json = {
                "params": {
                    "reportId": report_id
                },
                "jsonrpc": "2.0",
                "method": "deleteReport",
                "id": integration.company_id
            }

        result = requests.post(
            integration.base_url + "v1.0/jsonrpc/reports",
        json=json,
        verify=False,
        headers = {
        "Content-Type": "application/json",
        "Authorization": integration.auth_header
        }).json()

        return Response(result)