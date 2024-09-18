import re
from django.shortcuts import get_object_or_404

from allauth.socialaccount.models import SocialApp
from rest_framework.serializers import ModelSerializer, ReadOnlyField
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import AccountsPerms
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from knox.views import LoginView as KnoxLoginView
from django.contrib.auth import logout

class SocialAppSerializer(ModelSerializer):
    server_url = ReadOnlyField(source="settings.server_url")
    class Meta:
        model = SocialApp
        fields = [
            "id",
            "name",
            "provider",
            "provider_id",
            "client_id",
            "secret",
            "server_url",
            "settings",
        ]
        

class GetAddSSOProvider(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]

    def get(self, request):
        providers = SocialApp.objects.all()
        return Response(SocialAppSerializer(providers, many=True).data)

    class InputSerializer(ModelSerializer):
        server_url = ReadOnlyField()
        class Meta:
            model = SocialApp
            fields = [
                "name",
                "client_id",
                "secret",
                "server_url",
                "provider",
                "provider_id",
                "settings"
            ]

    # removed any special characters and replaces spaces with a hyphen
    def generate_provider_id(self, string):
        id = re.sub(r'[^A-Za-z0-9\s]', '', string)
        id = id.replace(' ', '-')
        return id

    def post(self, request):
        data = request.data

        # need to move server_url into json settings
        data["settings"] = {}
        data["settings"]["server_url"] = data["server_url"]

        # set provider to 'openid_connect'
        data["provider"] = "openid_connect"

        # generate a url friendly provider id from the name
        data["provider_id"] = self.generate_provider_id(data["name"])

        serializer = self.InputSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("ok")


class GetUpdateDeleteSSOProvider(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]

    class InputSerialzer(ModelSerializer):
        server_url = ReadOnlyField()
        class Meta:
            model = SocialApp
            fields = [
                "client_id",
                "secret",
                "server_url",
                "settings"
            ]   

    def put(self, request, pk):
        provider = get_object_or_404(SocialApp, pk=pk)
        data = request.data

        # need to move server_url into json settings
        data["settings"] = {}
        data["settings"]["server_url"] = data["server_url"]

        serializer = self.InputSerialzer(instance=provider, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("ok")

    def delete(self, request, pk):
        provider = get_object_or_404(SocialApp, pk=pk)
        provider.delete()
        return Response("ok")


class GetAccessToken(KnoxLoginView):
  permission_classes = [IsAuthenticated]
  authentication_classes = [SessionAuthentication]

  def post(self, request, format=None):
      response = super().post(request, format=None)
      response.data["username"] = request.user.username

      #invalid user session since we have an access token now
      logout(request)
      return Response(response.data)
        
