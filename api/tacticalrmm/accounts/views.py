import pyotp

from django.contrib.auth import login
from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.authtoken.serializers import AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import User
from agents.models import Agent

from .serializers import UserSerializer, TOTPSetupSerializer


class CheckCreds(KnoxLoginView):

    permission_classes = (AllowAny,)

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_object_or_404(User, username=request.data["username"])

        if not user.totp_key:
            return Response("totp not set")

        return Response("ok")


class LoginView(KnoxLoginView):

    permission_classes = (AllowAny,)

    def post(self, request, format=None):
        valid = False

        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        token = request.data["twofactor"]
        totp = pyotp.TOTP(user.totp_key)

        if settings.DEBUG and token == "sekret":
            valid = True
        elif totp.verify(token, valid_window=1):
            valid = True

        if valid:
            login(request, user)
            return super(LoginView, self).post(request, format=None)
        else:
            return Response("bad credentials", status=status.HTTP_400_BAD_REQUEST)


class GetAddUsers(APIView):
    def get(self, request):
        agents = Agent.objects.values_list("agent_id", flat=True)
        users = User.objects.exclude(username__in=agents)

        return Response(UserSerializer(users, many=True).data)

    def post(self, request):

        # Remove password from serializer
        password = request.data.pop("password")

        serializer = UserSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Can be changed once permissions and groups are introduced
        user.is_superuser = True
        user.set_password = password
        user.save()

        return Response("ok")


class GetUpdateDeleteUser(APIView):
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        return Response(UserSerializer(user).data)

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        serializer = UserSerializer(instance=user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(User, pk=pk).delete()

        return Response("ok")


class UserActions(APIView):

    # reset password
    def post(self, request):

        user = get_object_or_404(User, pk=request.data["id"])
        user.set_password(request.data["password"])
        user.save()

        return Response("ok")

    # reset two factor token
    def put(self, request):

        user = get_object_or_404(User, pk=request.data["id"])
        user.totp_key = ""
        user.save()

        return Response("ok")


class TOTPSetup(APIView):

    permission_classes = (AllowAny,)

    # totp setup
    def post(self, request):

        user = get_object_or_404(User, username=request.data["username"])

        if not user.totp_key:
            code = pyotp.random_base32()
            user.totp_key = code
            user.save(update_fields=["totp_key"])
            return Response(TOTPSetupSerializer(user).data)

        return Response("TOTP token already set")

