import threading

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

request_local = threading.local()


def get_username():
    return getattr(request_local, "username", None)


def get_debug_info():
    return getattr(request_local, "debug_info", {})


EXCLUDE_PATHS = (
    "/api/v3",
    "/logs/auditlogs",
    f"/{settings.ADMIN_URL}",
    "/logout",
    "/agents/installagent",
    "/logs/downloadlog",
)

ENDS_WITH = "/services/"


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.path.startswith(EXCLUDE_PATHS) and not request.path.endswith(
            ENDS_WITH
        ):
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
            try:
                if hasattr(request, "user") and request.user.is_authenticated:

                    debug_info = {}
                    # gather and save debug info
                    debug_info["url"] = request.path
                    debug_info["method"] = request.method
                    debug_info["view_class"] = view_func.cls.__name__
                    debug_info["view_func"] = view_func.__name__
                    debug_info["view_args"] = view_args
                    debug_info["view_kwargs"] = view_kwargs

                    request_local.debug_info = debug_info

                    # get authenticated user after request
                    request_local.username = request.user.username
            except AuthenticationFailed:
                pass

    def process_exception(self, request, exception):
        request_local.debug_info = None
        request_local.username = None

    def process_template_response(self, request, response):
        request_local.debug_info = None
        request_local.username = None
        return response
