import pyotp

from django.contrib.auth import login
from django.conf import settings

from rest_framework.authtoken.serializers import AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from accounts.models import User


class CheckCreds(KnoxLoginView):

    permission_classes = (AllowAny,)

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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


@api_view(["POST"])
@authentication_classes((BasicAuthentication,))
@permission_classes((IsAuthenticated,))
def installer_twofactor(request):

    token = request.data["twofactorToken"]
    totp = pyotp.TOTP(request.user.totp_key)

    if settings.DEBUG and token == "sekret":
        return Response("ok")
    elif totp.verify(token, valid_window=1):
        return Response("ok")
    else:
        return Response("bad 2 factor code", status=status.HTTP_400_BAD_REQUEST)
