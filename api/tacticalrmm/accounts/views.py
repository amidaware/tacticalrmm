import pyotp
from django.conf import settings
from django.contrib.auth import login
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from knox.views import LoginView as KnoxLoginView
from rest_framework import status
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from logs.models import AuditLog
from tacticalrmm.utils import notify_error

from .models import User, Role
from .permissions import AccountsPerms, RolesPerms
from .serializers import (
    TOTPSetupSerializer,
    UserSerializer,
    UserUISerializer,
    RoleSerializer,
)


def _is_root_user(request, user) -> bool:
    return (
        hasattr(settings, "ROOT_USER")
        and request.user != user
        and user.username == settings.ROOT_USER
    )


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
        elif totp.verify(token, valid_window=10):
            valid = True

        if valid:
            login(request, user)
            AuditLog.audit_user_login_successful(request.data["username"])
            return super(LoginView, self).post(request, format=None)
        else:
            AuditLog.audit_user_failed_twofactor(request.data["username"])
            return Response("bad credentials", status=status.HTTP_400_BAD_REQUEST)


class GetAddUsers(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]

    def get(self, request):
        users = User.objects.filter(agent=None, is_installer_user=False)

        return Response(UserSerializer(users, many=True).data)

    def post(self, request):
        # add new user
        try:
            user = User.objects.create_user(  # type: ignore
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
        if "role" in request.data.keys() and isinstance(request.data["role"], int):
            role = get_object_or_404(Role, pk=request.data["role"])
            user.role = role

        user.save()
        return Response(user.username)


class GetUpdateDeleteUser(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        return Response(UserSerializer(user).data)

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if _is_root_user(request, user):
            return notify_error("The root user cannot be modified from the UI")

        serializer = UserSerializer(instance=user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if _is_root_user(request, user):
            return notify_error("The root user cannot be deleted from the UI")

        user.delete()

        return Response("ok")


class UserActions(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]
    # reset password
    def post(self, request):
        user = get_object_or_404(User, pk=request.data["id"])
        if _is_root_user(request, user):
            return notify_error("The root user cannot be modified from the UI")

        user.set_password(request.data["password"])
        user.save()

        return Response("ok")

    # reset two factor token
    def put(self, request):
        user = get_object_or_404(User, pk=request.data["id"])
        if _is_root_user(request, user):
            return notify_error("The root user cannot be modified from the UI")

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
        serializer = UserUISerializer(
            instance=request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("ok")


class PermsList(APIView):
    def get(self, request):
        return Response(Role.perms())


class GetAddRoles(APIView):
    permission_classes = [IsAuthenticated, RolesPerms]

    def get(self, request):
        roles = Role.objects.all()
        return Response(RoleSerializer(roles, many=True).data)

    def post(self, request):
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("ok")


class GetUpdateDeleteRole(APIView):
    permission_classes = [IsAuthenticated, RolesPerms]

    def get(self, request, pk):
        role = get_object_or_404(Role, pk=pk)
        return Response(RoleSerializer(role).data)

    def put(self, request, pk):
        role = get_object_or_404(Role, pk=pk)
        serializer = RoleSerializer(instance=role, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("ok")

    def delete(self, request, pk):
        role = get_object_or_404(Role, pk=pk)
        role.delete()
        return Response("ok")
