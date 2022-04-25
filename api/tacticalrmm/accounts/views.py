import pyotp
from django.conf import settings
from django.contrib.auth import login
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from ipware import get_client_ip
from knox.views import LoginView as KnoxLoginView
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from logs.models import AuditLog
from tacticalrmm.helpers import notify_error

from .models import APIKey, Role, User
from .permissions import AccountsPerms, APIKeyPerms, RolesPerms
from .serializers import (
    APIKeySerializer,
    RoleSerializer,
    TOTPSetupSerializer,
    UserSerializer,
    UserUISerializer,
)


def _is_root_user(request, user) -> bool:
    root = (
        hasattr(settings, "ROOT_USER")
        and request.user != user
        and user.username == settings.ROOT_USER
    )
    demo = (
        getattr(settings, "DEMO", False) and request.user.username == settings.ROOT_USER
    )
    return root or demo


class CheckCreds(KnoxLoginView):

    permission_classes = (AllowAny,)

    def post(self, request, format=None):

        # check credentials
        serializer = AuthTokenSerializer(data=request.data)
        if not serializer.is_valid():
            AuditLog.audit_user_failed_login(
                request.data["username"], debug_info={"ip": request._client_ip}
            )
            return notify_error("Bad credentials")

        user = serializer.validated_data["user"]

        if user.block_dashboard_login:
            return notify_error("Bad credentials")

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

        if user.block_dashboard_login:
            return notify_error("Bad credentials")

        token = request.data["twofactor"]
        totp = pyotp.TOTP(user.totp_key)

        if settings.DEBUG and token == "sekret":
            valid = True
        elif getattr(settings, "DEMO", False):
            valid = True
        elif totp.verify(token, valid_window=10):
            valid = True

        if valid:
            login(request, user)

            # save ip information
            client_ip, is_routable = get_client_ip(request)
            user.last_login_ip = client_ip
            user.save()

            AuditLog.audit_user_login_successful(
                request.data["username"], debug_info={"ip": request._client_ip}
            )
            return super(LoginView, self).post(request, format=None)
        else:
            AuditLog.audit_user_failed_twofactor(
                request.data["username"], debug_info={"ip": request._client_ip}
            )
            return notify_error("Bad credentials")


class GetAddUsers(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]

    def get(self, request):
        search = request.GET.get("search", None)

        if search:
            users = User.objects.filter(agent=None, is_installer_user=False).filter(
                username__icontains=search
            )
        else:
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

        if "first_name" in request.data.keys():
            user.first_name = request.data["first_name"]
        if "last_name" in request.data.keys():
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


class GetAddRoles(APIView):
    permission_classes = [IsAuthenticated, RolesPerms]

    def get(self, request):
        roles = Role.objects.all()
        return Response(RoleSerializer(roles, many=True).data)

    def post(self, request):
        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("Role was added")


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
        return Response("Role was edited")

    def delete(self, request, pk):
        role = get_object_or_404(Role, pk=pk)
        role.delete()
        return Response("Role was removed")


class GetAddAPIKeys(APIView):
    permission_classes = [IsAuthenticated, APIKeyPerms]

    def get(self, request):
        apikeys = APIKey.objects.all()
        return Response(APIKeySerializer(apikeys, many=True).data)

    def post(self, request):
        # generate a random API Key
        from django.utils.crypto import get_random_string

        request.data["key"] = get_random_string(length=32).upper()
        serializer = APIKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response("The API Key was added")


class GetUpdateDeleteAPIKey(APIView):
    permission_classes = [IsAuthenticated, APIKeyPerms]

    def put(self, request, pk):
        apikey = get_object_or_404(APIKey, pk=pk)

        # remove API key is present in request data
        if "key" in request.data.keys():
            request.data.pop("key")

        serializer = APIKeySerializer(instance=apikey, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("The API Key was edited")

    def delete(self, request, pk):
        apikey = get_object_or_404(APIKey, pk=pk)
        apikey.delete()
        return Response("The API Key was deleted")
