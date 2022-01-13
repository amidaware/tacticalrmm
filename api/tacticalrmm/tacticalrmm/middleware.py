import threading

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from ipware import get_client_ip

request_local = threading.local()


def get_username():
    return getattr(request_local, "username", None)


def get_debug_info():
    return getattr(request_local, "debug_info", {})


EXCLUDE_PATHS = (
    "/api/v3",
    "/logs/audit",
    f"/{settings.ADMIN_URL}",
    "/logout",
    "/agents/installer",
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
                    debug_info["ip"] = request._client_ip

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


class LogIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        client_ip, is_routable = get_client_ip(request)

        request._client_ip = client_ip
        response = self.get_response(request)
        return response


class DemoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        self.not_allowed = [
            {"name": "AgentProcesses", "methods": ["DELETE"]},
            {"name": "AgentMeshCentral", "methods": ["GET", "POST"]},
            {"name": "update_agents", "methods": ["POST"]},
            {"name": "send_raw_cmd", "methods": ["POST"]},
            {"name": "install_agent", "methods": ["POST"]},
            {"name": "get_mesh_exe", "methods": ["POST"]},
            {"name": "GenerateAgent", "methods": ["GET"]},
            {"name": "UploadMeshAgent", "methods": ["PUT"]},
            {"name": "email_test", "methods": ["POST"]},
            {"name": "server_maintenance", "methods": ["POST"]},
            {"name": "CodeSign", "methods": ["PATCH", "POST"]},
            {"name": "TwilioSMSTest", "methods": ["POST"]},
            {"name": "GetEditActionService", "methods": ["PUT", "POST"]},
            {"name": "TestScript", "methods": ["POST"]},
            {"name": "GetUpdateDeleteAgent", "methods": ["DELETE"]},
            {"name": "Reboot", "methods": ["POST", "PATCH"]},
            {"name": "recover", "methods": ["POST"]},
            {"name": "run_script", "methods": ["POST"]},
            {"name": "bulk", "methods": ["POST"]},
            {"name": "WMI", "methods": ["POST"]},
            {"name": "PolicyAutoTask", "methods": ["POST"]},
            {"name": "RunAutoTask", "methods": ["POST"]},
            {"name": "run_checks", "methods": ["POST"]},
            {"name": "GetSoftware", "methods": ["POST", "PUT"]},
            {"name": "ScanWindowsUpdates", "methods": ["POST"]},
            {"name": "InstallWindowsUpdates", "methods": ["POST"]},
            {"name": "PendingActions", "methods": ["DELETE"]},
        ]

    def __call__(self, request):
        return self.get_response(request)

    def drf_mock_response(self, request, resp):
        from rest_framework.views import APIView

        view = APIView()
        view.headers = view.default_response_headers
        return view.finalize_response(request, resp).render()  # type: ignore

    def process_view(self, request, view_func, view_args, view_kwargs):
        from .utils import notify_error

        err = "Not available in demo"
        excludes = ("/api/v3",)

        if request.path.startswith(excludes):
            return self.drf_mock_response(request, notify_error(err))

        for i in self.not_allowed:
            if view_func.__name__ == i["name"] and request.method in i["methods"]:
                return self.drf_mock_response(request, notify_error(err))
