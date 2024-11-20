import datetime

import pyotp
from allauth.socialaccount.models import SocialAccount, SocialApp
from django.conf import settings
from django.contrib.auth import login
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from knox.models import AuthToken
from knox.views import LoginView as KnoxLoginView
from python_ipware import IpWare
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import (
    ModelSerializer,
    ReadOnlyField,
    SerializerMethodField,
)
from rest_framework.views import APIView

from accounts.utils import is_root_user
from core.tasks import sync_mesh_perms_task
from logs.models import AuditLog
from tacticalrmm.helpers import notify_error
from tacticalrmm.utils import get_core_settings

from .models import APIKey, Role, User
from .permissions import (
    AccountsPerms,
    APIKeyPerms,
    LocalUserPerms,
    RolesPerms,
    SelfResetSSOPerms,
)
from .serializers import (
    APIKeySerializer,
    RoleSerializer,
    TOTPSetupSerializer,
    UserSerializer,
    UserUISerializer,
)


class CheckCredsV2(KnoxLoginView):
    permission_classes = (AllowAny,)

    # restrict time on tokens issued by this view to 3 min
    def get_token_ttl(self):
        return datetime.timedelta(seconds=180)

    def post(self, request, format=None):
        # check credentials
        serializer = AuthTokenSerializer(data=request.data)
        if not serializer.is_valid():
            AuditLog.audit_user_failed_login(
                request.data["username"], debug_info={"ip": request._client_ip}
            )
            return notify_error("Bad credentials")

        user = serializer.validated_data["user"]

        if user.block_dashboard_login or user.is_sso_user:
            return notify_error("Bad credentials")

        # block local logon if configured
        core_settings = get_core_settings()
        if not user.is_superuser and core_settings.block_local_user_logon:
            return notify_error("Bad credentials")

        # if totp token not set modify response to notify frontend
        if not user.totp_key:
            login(request, user)
            response = super().post(request, format=None)
            response.data["totp"] = False
            return response

        return Response({"totp": True})


class LoginViewV2(KnoxLoginView):
    permission_classes = (AllowAny,)

    def post(self, request, format=None):
        valid = False

        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        if user.block_dashboard_login:
            return notify_error("Bad credentials")

        # block local logon if configured
        core_settings = get_core_settings()
        if not user.is_superuser and core_settings.block_local_user_logon:
            return notify_error("Bad credentials")

        if user.is_sso_user:
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
            ipw = IpWare()
            client_ip, _ = ipw.get_client_ip(request.META)
            if client_ip:
                user.last_login_ip = str(client_ip)
                user.save()

            AuditLog.audit_user_login_successful(
                request.data["username"], debug_info={"ip": request._client_ip}
            )
            response = super().post(request, format=None)
            response.data["username"] = request.user.username
            response.data["name"] = None

            return Response(response.data)
        else:
            AuditLog.audit_user_failed_twofactor(
                request.data["username"], debug_info={"ip": request._client_ip}
            )
            return notify_error("Bad credentials")


class GetDeleteActiveLoginSessionsPerUser(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]

    class TokenSerializer(ModelSerializer):
        user = ReadOnlyField(source="user.username")

        class Meta:
            model = AuthToken
            fields = (
                "digest",
                "user",
                "created",
                "expiry",
            )

    def get(self, request, pk):
        tokens = get_object_or_404(User, pk=pk).auth_token_set.filter(
            expiry__gt=djangotime.now()
        )

        return Response(self.TokenSerializer(tokens, many=True).data)

    def delete(self, request, pk):
        tokens = get_object_or_404(User, pk=pk).auth_token_set.filter(
            expiry__gt=djangotime.now()
        )

        tokens.delete()
        return Response("ok")


class DeleteActiveLoginSession(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]

    def delete(self, request, pk):
        token = get_object_or_404(AuthToken, digest=pk)

        token.delete()

        return Response("ok")


class GetAddUsers(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]

    class UserSerializerSSO(ModelSerializer):
        social_accounts = SerializerMethodField()

        def get_social_accounts(self, obj):
            accounts = SocialAccount.objects.filter(user_id=obj.pk)

            if accounts:
                social_accounts = []
                for account in accounts:
                    try:
                        provider_account = account.get_provider_account()
                        display = provider_account.to_str()
                    except SocialApp.DoesNotExist:
                        display = "Orphaned Provider"
                    except Exception:
                        display = "Unknown"

                    social_accounts.append(
                        {
                            "uid": account.uid,
                            "provider": account.provider,
                            "display": display,
                            "last_login": account.last_login,
                            "date_joined": account.date_joined,
                            "extra_data": account.extra_data,
                        }
                    )

                return social_accounts

            return []

        class Meta:
            model = User
            fields = [
                "id",
                "username",
                "first_name",
                "last_name",
                "email",
                "is_active",
                "last_login",
                "last_login_ip",
                "role",
                "block_dashboard_login",
                "date_format",
                "social_accounts",
            ]

    def get(self, request):
        search = request.GET.get("search", None)

        if search:
            users = User.objects.filter(agent=None, is_installer_user=False).filter(
                username__icontains=search
            )
        else:
            users = User.objects.filter(agent=None, is_installer_user=False)

        return Response(self.UserSerializerSSO(users, many=True).data)

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
        sync_mesh_perms_task.delay()
        return Response(user.username)


class GetUpdateDeleteUser(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        return Response(UserSerializer(user).data)

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if is_root_user(request=request, user=user):
            return notify_error("The root user cannot be modified from the UI")

        serializer = UserSerializer(instance=user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        sync_mesh_perms_task.delay()

        return Response("ok")

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if is_root_user(request=request, user=user):
            return notify_error("The root user cannot be deleted from the UI")

        user.delete()
        sync_mesh_perms_task.delay()
        return Response("ok")


class UserActions(APIView):
    permission_classes = [IsAuthenticated, AccountsPerms, LocalUserPerms]

    # reset password
    def post(self, request):
        user = get_object_or_404(User, pk=request.data["id"])
        if is_root_user(request=request, user=user):
            return notify_error("The root user cannot be modified from the UI")

        user.set_password(request.data["password"])
        user.save()

        return Response("ok")

    # reset two factor token
    def put(self, request):
        user = get_object_or_404(User, pk=request.data["id"])
        if is_root_user(request=request, user=user):
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

        return Response(False)


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
        sync_mesh_perms_task.delay()
        return Response("Role was edited")

    def delete(self, request, pk):
        role = get_object_or_404(Role, pk=pk)
        role.delete()
        sync_mesh_perms_task.delay()
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
        serializer.save()
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


class ResetPass(APIView):
    permission_classes = [IsAuthenticated, SelfResetSSOPerms]

    def put(self, request):
        user = request.user
        user.set_password(request.data["password"])
        user.save()
        return Response("Password was reset.")


class Reset2FA(APIView):
    permission_classes = [IsAuthenticated, SelfResetSSOPerms]

    def put(self, request):
        user = request.user
        user.totp_key = ""
        user.save()
        return Response("2FA was reset. Log out and back in to setup.")
