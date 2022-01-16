from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from .models import Integration
from .serializers import GetIntegrationsSerializer, GetIntegrationSerializer

class GetIntegrations(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        integrations = Integration.objects.all().order_by('name')
        serializer = GetIntegrationsSerializer(integrations, many=True)

        return Response(serializer.data)

class GetIntegration(APIView):
    permission_classes = [IsAuthenticated]

    # serializer_class = GetIntegrationsSerializer
    def get(self, request, pk):
        integration = get_object_or_404(Integration, pk=pk)
        return Response(GetIntegrationSerializer(integration).data)

    def post(self, request, pk):
        integration = get_object_or_404(Integration, pk=pk)
        if request.data['enabled'] == True:
            integration.configuration['api_key'] = request.data['apikey']
            integration.configuration['api_url'] = request.data['apiurl']
            integration.configuration['company_id'] = request.data['companyID']
            integration.enabled = True
            # integration.configuration['tactical_meraki_associations'] = [{'id':1, 'name':'osborn'},{'id':2, 'name':'dea'}]
            integration.save()

            return Response("ok")
        else:
            integration.configuration['api_key'] = ""
            integration.configuration['api_url'] = ""
            integration.configuration['company_id'] = ""
            integration.enabled = False
            integration.save()

            return Response("ok")

    def put(self, request, pk):
        integration = get_object_or_404(Integration, pk=pk)
        print(request.data)
        if request.data['associate'] == True:
            integration.configuration['tactical_meraki_associations'].append(request.data)
            integration.save()
            return Response("ok")
        else:
            integration.configuration['api_key'] = request.data['apikey']
            integration.configuration['api_url'] = request.data['apiurl']
            integration.configuration['company_id'] = request.data['companyID']
            # integration.configuration['tactical_meraki_associations'] = [{'id':1, 'name':'osborn'},{'id':2, 'name':'dea'}]
            integration.save()

            return Response("ok")