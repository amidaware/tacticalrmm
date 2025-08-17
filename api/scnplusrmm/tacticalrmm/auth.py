from django.utils import timezone as djangotime
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import HTTP_HEADER_ENCODING, BaseAuthentication

from accounts.models import APIKey


def get_authorization_header(request) -> str:
    """
    Return request's 'Authorization:' header, as a bytestring.

    Hide some test client ickyness where the header can be unicode.
    """
    auth = request.META.get("HTTP_X_API_KEY", b"")
    if isinstance(auth, str):
        # Work around django test client oddness
        auth = auth.encode(HTTP_HEADER_ENCODING)
    return auth


class APIAuthentication(BaseAuthentication):
    """
    Simple token based authentication for stateless api access.

    Clients should authenticate by passing the token key in the "X-API-KEY"
    HTTP header.  For example:

        X-API-KEY: ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
    """

    def get_model(self):
        return APIKey

    def authenticate(self, request):
        auth = get_authorization_header(request)

        if not auth:
            return None

        try:
            apikey = auth.decode()  # type: ignore
        except UnicodeError:
            msg = _(
                "Invalid token header. Token string should not contain invalid characters."
            )
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(apikey)

    def authenticate_credentials(self, key):
        try:
            apikey = APIKey.objects.select_related("user").get(key=key)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        if not apikey.user.is_active:
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        # check if token is expired
        if apikey.expiration and apikey.expiration < djangotime.now():
            raise exceptions.AuthenticationFailed(_("The token has expired."))

        return apikey.user, apikey.key
