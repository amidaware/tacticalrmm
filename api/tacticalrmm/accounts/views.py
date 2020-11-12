import pyotp

from django.contrib.auth import login
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import IntegrityError

from rest_framework.views import APIView
from rest_framework.authtoken.serializers import AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import User
from agents.models import Agent
from logs.models import AuditLog
from tacticalrmm.utils import notify_error

from .serializers import UserSerializer, TOTPSetupSerializer


class CheckCreds(KnoxLoginView):

    permission_classes = (AllowAny,)

    def post(self, request, format=None):

        # check credentials
        serializer = AuthTokenSerializer(data=request.data)
        if not serializer.is_valid():
            AuditLog.audit_user_failed_login(request.data["username"])
            return Response("bad credentials", status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]

        # if totp token not set modify response to notify frontend
        if not user.totp_key:
            login(request, user)
            response = super(CheckCreds, self).post(request, format=None)
            response.data["totp"] = "totp not set"
            return response

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
            AuditLog.audit_user_login_successful(request.data["username"])
            return super(LoginView, self).post(request, format=None)
        else:
            AuditLog.audit_user_failed_twofactor(request.data["username"])
            return Response("bad credentials", status=status.HTTP_400_BAD_REQUEST)


class GetAddUsers(APIView):
    def get(self, request):
        users = User.objects.filter(agent=None)

        return Response(UserSerializer(users, many=True).data)

    def post(self, request):
        # add new user
        try:
            user = User.objects.create_user(
                request.data["username"],
                request.data["email"],
                request.data["password"],
            )
        except IntegrityError:
            return notify_error(
                f"ERROR: User {request.data['username']} already exists!"
            )

        user.first_name = request.data["first_name"]
        user.last_name = request.data["last_name"]
        # Can be changed once permissions and groups are introduced
        user.is_superuser = True
        user.save()
        return Response(user.username)


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

        return Response(
            f"{user.username}'s Two-Factor key was reset. Have them sign in again to setup"
        )


class TOTPSetup(APIView):

    # totp setup
    def post(self, request):

        user = request.user
        if not user.totp_key:
            code = pyotp.random_base32()
            user.totp_key = code
            user.save(update_fields=["totp_key"])
            return Response(TOTPSetupSerializer(user).data)

        return Response("totp token already set")


class UserUI(APIView):
    def patch(self, request):
        user = request.user
        user.dark_mode = request.data["dark_mode"]
        user.save(update_fields=["dark_mode"])
        return Response("ok")