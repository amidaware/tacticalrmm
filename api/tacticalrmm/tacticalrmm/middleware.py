import threading
from contextlib import suppress
from typing import Any, Dict, Optional

from django.conf import settings
from python_ipware import IpWare
from rest_framework.exceptions import AuthenticationFailed

from tacticalrmm.constants import DEMO_NOT_ALLOWED
from tacticalrmm.helpers import notify_error

request_local = threading.local()


def get_username() -> Optional[str]:
    return getattr(request_local, "username", None)


def get_debug_info() -> Dict[str, Any]:
    return getattr(request_local, "debug_info", {})


EXCLUDE_PATHS = (
    "/api/v3",
    "/logs/audit",
    f"/{settings.ADMIN_URL}",
    "/logout",
    "/agents/installer",
    "/api/schema",
    "/accounts/ssoproviders/token",
    "/_allauth/browser/v1/config",
    "/_allauth/browser/v1/auth/provider/redirect",
)

DEMO_EXCLUDE_PATHS = (
    "/api/v3",
    "/api/schema",
)


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.path.startswith(EXCLUDE_PATHS):
            # https://stackoverflow.com/questions/26240832/django-and-middleware-which-uses-request-user-is-always-anonymous
            try:
                # DRF saves the class of the view function as the .cls property
                view_class = view_func.cls
                # We need to instantiate the class
                view = view_class()
                # And give it an action_map. It's not relevant for us, but otherwise it errors.
                view.action_map = {}
                # Here's our fully formed and authenticated (or not, depending on credentials) request
                request = view.initialize_request(request)
            except (AttributeError, TypeError):
                from rest_framework.views import APIView

                # Can't initialize the request from this view. Fallback to using default permission classes
                request = APIView().initialize_request(request)

            # check if user is authenticated
            with suppress(AuthenticationFailed):
                if hasattr(request, "user") and request.user.is_authenticated:
                    try:
                        view_Name = view_func.__dict__["view_class"].__name__
                    except:
                        view_Name = view_func.__name__
                    debug_info = {}
                    # gather and save debug info
                    debug_info["url"] = request.path
                    debug_info["method"] = request.method
                    debug_info["view_class"] = (
                        view_func.cls.__name__ if hasattr(view_func, "cls") else None
                    )
                    debug_info["view_func"] = view_Name
                    debug_info["view_args"] = view_args
                    debug_info["view_kwargs"] = view_kwargs
                    debug_info["ip"] = request._client_ip

                    request_local.debug_info = debug_info

                    # get authenticated user after request
                    request_local.username = request.user.username

    def process_exception(self, request, exception):
        request_local.debug_info = None
        request_local.username = None

    def process_template_response(self, request, response):
        request_local.debug_info = None
        request_local.username = None
        return response


class LogIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ipw = IpWare()
        client_ip, _ = ipw.get_client_ip(request.META)

        request._client_ip = str(client_ip) if client_ip else ""
        response = self.get_response(request)
        return response


class DemoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        self.not_allowed = DEMO_NOT_ALLOWED

    def __call__(self, request):
        return self.get_response(request)

    def drf_mock_response(self, request, resp):
        from rest_framework.views import APIView

        view = APIView()
        view.headers = view.default_response_headers
        return view.finalize_response(request, resp).render()

    def process_view(self, request, view_func, view_args, view_kwargs):
        err = "Not available in demo"
        if request.path.startswith(DEMO_EXCLUDE_PATHS):
            return self.drf_mock_response(request, notify_error(err))

        try:
            view_Name = view_func.__dict__["view_class"].__name__
        except:
            return
        for i in self.not_allowed:
            if view_Name == i["name"] and request.method in i["methods"]:
                return self.drf_mock_response(request, notify_error(err))
