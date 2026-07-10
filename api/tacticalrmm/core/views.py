import json
from contextlib import suppress
from pathlib import Path

import psutil
import requests
import validators
from cryptography import x509
from django.conf import settings
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from django.views.decorators.csrf import csrf_exempt
from redis import from_url
from rest_framework import serializers
from rest_framework import status as drf_status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import monitoring_view, monitoring_view_v2
from core.tasks import sync_mesh_perms_task
from core.utils import (
    get_core_settings,
    run_server_script,
    run_test_url_rest_action,
    sysd_svc_is_running,
    token_is_valid,
)
from logs.models import AuditLog
from tacticalrmm.constants import AuditActionType, PAStatus
from tacticalrmm.helpers import get_certs, notify_error
from tacticalrmm.logger import logger
from tacticalrmm.permissions import (
    _has_perm_on_agent,
    _has_perm_on_client,
    _has_perm_on_site,
)

from .models import (
    AIModel,
    AIProvider,
    AITask,
    AITaskRun,
    BulkAICommand,
    CodeSignToken,
    CoreSettings,
    CustomField,
    GlobalKVStore,
    Schedule,
    URLAction,
)
from .permissions import (
    AITaskPerms,
    BulkAIPerms,
    CodeSignPerms,
    CoreSettingsPerms,
    CustomFieldPerms,
    GlobalKeyStorePerms,
    RunServerScriptPerms,
    SchedulePerms,
    ServerMaintPerms,
    URLActionPerms,
    WebTerminalPerms,
)
from .serializers import (
    AIModelSerializer,
    AIProviderSerializer,
    AITaskSerializer,
    AITaskRunSerializer,
    BulkAICommandSerializer,
    CodeSignTokenSerializer,
    CoreSettingsSerializer,
    CustomFieldSerializer,
    KeyStoreSerializer,
    ScheduleSerializer,
    URLActionSerializer,
)


class GetEditCoreSettings(APIView):
    permission_classes = [IsAuthenticated, CoreSettingsPerms]

    def get(self, request):
        settings = CoreSettings.objects.first()
        return Response(CoreSettingsSerializer(settings).data)

    def put(self, request):
        data = request.data.copy()

        if getattr(settings, "HOSTED", False):
            data.pop("mesh_site")
            data.pop("mesh_token")
            data.pop("mesh_username")
            data["sync_mesh_with_trmm"] = True
            data["enable_server_scripts"] = False
            data["enable_server_webterminal"] = False

        coresettings = CoreSettings.objects.first()
        serializer = CoreSettingsSerializer(
            instance=coresettings, data=data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        sync_mesh_perms_task.delay()

        return Response("ok")


@api_view()
@permission_classes([AllowAny])
def home(request):
    return Response({"status": "ok"})


@api_view()
def version(request):
    return Response(settings.APP_VER)


@api_view()
@permission_classes([IsAuthenticated, ServerMaintPerms])
def clear_cache(request):
    from core.utils import clear_entire_cache

    clear_entire_cache()
    return Response("Cache was cleared!")


@api_view()
def dashboard_info(request):
    if request.user.is_installer_user:
        return notify_error("")

    from core.utils import token_is_expired
    from tacticalrmm.utils import get_latest_trmm_ver, runcmd_placeholder_text

    core_settings = get_core_settings()
    return Response(
        {
            "trmm_version": settings.TRMM_VERSION,
            "latest_trmm_ver": get_latest_trmm_ver(),
            "dark_mode": request.user.dark_mode,
            "show_community_scripts": request.user.show_community_scripts,
            "dbl_click_action": request.user.agent_dblclick_action,
            "default_agent_tbl_tab": request.user.default_agent_tbl_tab,
            "url_action": (
                request.user.url_action.id if request.user.url_action else None
            ),
            "client_tree_sort": request.user.client_tree_sort,
            "client_tree_splitter": request.user.client_tree_splitter,
            "loading_bar_color": request.user.loading_bar_color,
            "clear_search_when_switching": request.user.clear_search_when_switching,
            "hosted": getattr(settings, "HOSTED", False),
            "date_format": request.user.date_format,
            "default_date_format": core_settings.date_format,
            "token_is_expired": token_is_expired(),
            "open_ai_integration_enabled": bool(core_settings.open_ai_token),
            "dash_info_color": request.user.dash_info_color,
            "dash_positive_color": request.user.dash_positive_color,
            "dash_negative_color": request.user.dash_negative_color,
            "dash_warning_color": request.user.dash_warning_color,
            "run_cmd_placeholder_text": runcmd_placeholder_text(),
            "server_scripts_enabled": core_settings.server_scripts_enabled,
            "web_terminal_enabled": core_settings.web_terminal_enabled,
            "block_local_user_logon": core_settings.block_local_user_logon,
            "sso_enabled": core_settings.sso_enabled,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, CoreSettingsPerms])
def email_test(request):
    core = get_core_settings()

    msg, ok = core.send_mail(
        subject="Test from Tactical RMM", body="This is a test message", test=True
    )
    if not ok:
        return notify_error(msg)

    return Response(msg)


@api_view(["POST"])
@permission_classes([IsAuthenticated, ServerMaintPerms])
def server_maintenance(request):
    from tacticalrmm.utils import reload_nats

    if "action" not in request.data:
        return notify_error("The data is incorrect")

    if request.data["action"] == "reload_nats":
        reload_nats()
        return Response("Nats configuration was reloaded successfully.")

    if request.data["action"] == "rm_orphaned_tasks":
        from autotasks.tasks import remove_orphaned_win_tasks

        remove_orphaned_win_tasks.delay()
        return Response("The task has been initiated.")

    if request.data["action"] == "prune_db":
        from logs.models import AuditLog, PendingAction

        if "prune_tables" not in request.data:
            return notify_error("The data is incorrect.")

        tables = request.data["prune_tables"]
        records_count = 0
        if "audit_logs" in tables:
            auditlogs = AuditLog.objects.filter(action=AuditActionType.CHECK_RUN)
            records_count += auditlogs.count()
            auditlogs.delete()

        if "pending_actions" in tables:
            pendingactions = PendingAction.objects.filter(status=PAStatus.COMPLETED)
            records_count += pendingactions.count()
            pendingactions.delete()

        if "alerts" in tables:
            from alerts.models import Alert

            alerts = Alert.objects.all()
            records_count += alerts.count()
            alerts.delete()

        return Response(f"{records_count} records were pruned from the database")

    return notify_error("The data is incorrect")


class GetAddCustomFields(APIView):
    permission_classes = [IsAuthenticated, CustomFieldPerms]

    def get(self, request):
        if "model" in request.query_params.keys():
            fields = CustomField.objects.filter(model=request.query_params["model"])
        else:
            fields = CustomField.objects.all()
        return Response(CustomFieldSerializer(fields, many=True).data)

    def patch(self, request):
        if "model" in request.data.keys():
            fields = CustomField.objects.filter(model=request.data["model"])
            return Response(CustomFieldSerializer(fields, many=True).data)

        return notify_error("The request was invalid")

    def post(self, request):
        serializer = CustomFieldSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")


class GetUpdateDeleteCustomFields(APIView):
    permission_classes = [IsAuthenticated, CustomFieldPerms]

    def get(self, request, pk):
        custom_field = get_object_or_404(CustomField, pk=pk)

        return Response(CustomFieldSerializer(custom_field).data)

    def put(self, request, pk):
        custom_field = get_object_or_404(CustomField, pk=pk)

        serializer = CustomFieldSerializer(
            instance=custom_field, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(CustomField, pk=pk).delete()

        return Response("ok")


class CodeSign(APIView):
    permission_classes = [IsAuthenticated, CodeSignPerms]

    def get(self, request):
        token = CodeSignToken.objects.first()
        return Response(CodeSignTokenSerializer(token).data)

    def patch(self, request):
        import requests

        token = request.data["token"].strip().replace(" ", "").lower()
        if not validators.uuid(token):
            return notify_error("Invalid token format.")

        try:
            r = requests.post(
                settings.CHECK_TOKEN_URL,
                json={"token": token, "api": settings.ALLOWED_HOSTS[0]},
                headers={"Content-type": "application/json"},
                timeout=15,
            )
        except Exception as e:
            return notify_error(str(e))

        if r.status_code in (400, 401):
            return notify_error(r.json()["ret"])
        elif r.status_code == 200:
            t = CodeSignToken.objects.first()
            if t is None:
                CodeSignToken.objects.create(token=token)
            else:
                t.token = token
                t.save(update_fields=["token"])
            return Response("Token was saved")

        try:
            ret = r.json()["ret"]
        except:
            ret = "Something went wrong"
        return notify_error(ret)

    def post(self, request):
        from agents.models import Agent
        from agents.tasks import send_agent_update_task

        token, is_valid = token_is_valid()
        if not is_valid:
            return notify_error("Invalid token")

        agent_ids: list[str] = list(
            Agent.objects.only("pk", "agent_id").values_list("agent_id", flat=True)
        )
        send_agent_update_task.delay(agent_ids=agent_ids, token=token, force=True)
        return Response("Agents will be code signed shortly")

    def delete(self, request):
        CodeSignToken.objects.all().delete()
        return Response("ok")


class GetAddKeyStore(APIView):
    permission_classes = [IsAuthenticated, GlobalKeyStorePerms]

    def get(self, request):
        keys = GlobalKVStore.objects.all()
        return Response(KeyStoreSerializer(keys, many=True).data)

    def post(self, request):
        serializer = KeyStoreSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")


class UpdateDeleteKeyStore(APIView):
    permission_classes = [IsAuthenticated, GlobalKeyStorePerms]

    def put(self, request, pk):
        key = get_object_or_404(GlobalKVStore, pk=pk)

        serializer = KeyStoreSerializer(instance=key, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(GlobalKVStore, pk=pk).delete()

        return Response("ok")


class GetAddURLAction(APIView):
    permission_classes = [IsAuthenticated, URLActionPerms]

    def get(self, request):
        actions = URLAction.objects.all()
        return Response(URLActionSerializer(actions, many=True).data)

    def post(self, request):
        serializer = URLActionSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")


class UpdateDeleteURLAction(APIView):
    permission_classes = [IsAuthenticated, CoreSettingsPerms]

    def put(self, request, pk):
        action = get_object_or_404(URLAction, pk=pk)

        serializer = URLActionSerializer(
            instance=action, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(URLAction, pk=pk).delete()

        return Response("ok")


class RunURLAction(APIView):
    permission_classes = [IsAuthenticated, URLActionPerms]

    def patch(self, request):
        from requests.utils import requote_uri

        from agents.models import Agent
        from clients.models import Client, Site
        from tacticalrmm.utils import RE_DB_VALUE, get_db_value

        if "agent_id" in request.data.keys():
            if not _has_perm_on_agent(request.user, request.data["agent_id"]):
                raise PermissionDenied()

            instance = get_object_or_404(Agent, agent_id=request.data["agent_id"])
        elif "site" in request.data.keys():
            if not _has_perm_on_site(request.user, request.data["site"]):
                raise PermissionDenied()

            instance = get_object_or_404(Site, pk=request.data["site"])
        elif "client" in request.data.keys():
            if not _has_perm_on_client(request.user, request.data["client"]):
                raise PermissionDenied()

            instance = get_object_or_404(Client, pk=request.data["client"])
        else:
            return notify_error("received an incorrect request")

        action = get_object_or_404(URLAction, pk=request.data["action"])

        url_pattern = action.pattern

        for string, model, prop in RE_DB_VALUE.findall(url_pattern):
            value = get_db_value(string=f"{model}.{prop}", instance=instance)

            url_pattern = url_pattern.replace(string, str(value))

        AuditLog.audit_url_action(
            username=request.user.username,
            urlaction=action,
            instance=instance,
            debug_info={"ip": request._client_ip},
        )

        return Response(requote_uri(url_pattern))


class RunTestURLAction(APIView):
    permission_classes = [IsAuthenticated, URLActionPerms]

    class InputSerializer(serializers.Serializer):
        pattern = serializers.CharField(required=True)
        rest_body = serializers.CharField()
        rest_headers = serializers.CharField()
        rest_method = serializers.ChoiceField(
            required=True, choices=["get", "post", "put", "delete", "patch"]
        )
        run_instance_type = serializers.ChoiceField(
            choices=["agent", "client", "site", "none"]
        )
        run_instance_id = serializers.CharField(allow_null=True)

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data.get("pattern")
        body = serializer.validated_data.get("rest_body", None)
        headers = serializer.validated_data.get("rest_headers", None)
        method = serializer.validated_data.get("rest_method")
        instance_type = serializer.validated_data.get("run_instance_type", None)
        instance_id = serializer.validated_data.get("run_instance_id", None)

        # make sure user has permissions to run against client/agent/site
        if instance_type == "agent":
            if not _has_perm_on_agent(request.user, instance_id):
                raise PermissionDenied()

        elif instance_type == "site":
            if not _has_perm_on_site(request.user, instance_id):
                raise PermissionDenied()

        elif instance_type == "client":
            if not _has_perm_on_client(request.user, instance_id):
                raise PermissionDenied()

        result, replaced_url, replaced_body = run_test_url_rest_action(
            url=url,
            body=body,
            headers=headers,
            method=method,
            instance_type=instance_type,
            instance_id=instance_id,
        )

        AuditLog.audit_url_action_test(
            username=request.user.username,
            url=url,
            body=replaced_body,
            headers=headers,
            instance_type=instance_type,
            instance_id=instance_id,
            debug_info={"ip": request._client_ip},
        )

        return Response({"url": replaced_url, "result": result, "body": replaced_body})


class GetAddSchedule(APIView):
    permission_classes = [IsAuthenticated, SchedulePerms]

    def get(self, request):
        schedules = Schedule.objects.all()
        return Response(ScheduleSerializer(schedules, many=True).data)

    def post(self, request):
        serializer = ScheduleSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class UpdateDeleteSchedule(APIView):
    permission_classes = [IsAuthenticated, SchedulePerms]

    def put(self, request, pk):
        schedule = get_object_or_404(Schedule, pk=pk)

        serializer = ScheduleSerializer(
            instance=schedule, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def delete(self, request, pk):
        schedule = get_object_or_404(Schedule, pk=pk)

        try:
            schedule.delete()
        except IntegrityError:
            return notify_error("This schedule is currently in use.")

        return Response(pk)


class TestRunServerScript(APIView):
    permission_classes = [IsAuthenticated, RunServerScriptPerms]

    def post(self, request):
        core: CoreSettings = CoreSettings.objects.first()  # type: ignore
        if not core.server_scripts_enabled:
            return notify_error(
                "This feature is disabled. It can be enabled in Global Settings."
            )

        code: str = request.data["code"]
        if not code.startswith("#!"):
            return notify_error("Missing shebang!")

        stdout, stderr, execution_time, retcode = run_server_script(
            body=code,
            args=request.data["args"],
            env_vars=request.data["env_vars"],
            timeout=request.data["timeout"],
            shell=request.data["shell"],
        )

        ret = {
            "stdout": stdout,
            "stderr": stderr,
            "execution_time": f"{execution_time:.4f}",
            "retcode": retcode,
        }

        audit_before = {
            "body": code,
            "args": request.data["args"],
            "env_vars": request.data["env_vars"],
            "timeout": request.data["timeout"],
            "shell": request.data["shell"],
        }

        AuditLog.audit_test_script_run(
            username=request.user.username,
            before_value=audit_before,
            after_value=ret,
            agent=None,
            debug_info={"ip": request._client_ip},
        )

        return Response(ret)


@api_view(["POST"])
@permission_classes([IsAuthenticated, WebTerminalPerms])
def webterm_perms(request):
    # this view is only used to display a notification if feature is disabled
    # perms are actually enforced in the consumer
    core: CoreSettings = CoreSettings.objects.first()  # type: ignore
    if not core.web_terminal_enabled:
        ret = "This feature is disabled. It can be enabled in Global Settings."
        return Response(ret, status=drf_status.HTTP_412_PRECONDITION_FAILED)

    return Response("ok")


class TwilioSMSTest(APIView):
    permission_classes = [IsAuthenticated, CoreSettingsPerms]

    def post(self, request):
        core = get_core_settings()
        if not core.sms_is_configured:
            return notify_error(
                "All fields are required, including at least 1 recipient"
            )

        msg, ok = core.send_sms("TacticalRMM Test SMS", test=True)
        if not ok:
            return notify_error(msg)

        return Response(msg)


@csrf_exempt
@monitoring_view_v2
def status_v2(request):
    from agents.models import Agent
    from clients.models import Client, Site
    from tacticalrmm.helpers import get_nats_ports
    from tacticalrmm.utils import get_celery_queue_len, localhost_port_is_open

    disk_usage: int = round(psutil.disk_usage("/").percent)
    mem_usage: int = round(psutil.virtual_memory().percent)

    cert_file, _ = get_certs()
    cert_bytes = Path(cert_file).read_bytes()

    cert = x509.load_pem_x509_certificate(cert_bytes)
    delta = cert.not_valid_after_utc - djangotime.now()

    redis_url = f"redis://{settings.REDIS_HOST}"
    redis_ping = False
    with suppress(Exception):
        with from_url(redis_url) as conn:
            conn.ping()
            redis_ping = True

    celery_queue_health = "healthy"
    try:
        queue_len = get_celery_queue_len()
    except RuntimeError as e:
        queue_len = -1
        celery_queue_health = "unhealthy"
        logger.error(f"Error getting celery queue length: {e}")

    nats_std_port, nats_ws_port = get_nats_ports()
    mesh_port = getattr(settings, "MESH_PORT", 4430)

    ret = {
        "version": settings.TRMM_VERSION,
        "latest_agent_version": settings.LATEST_AGENT_VER,
        "agent_count": Agent.objects.count(),
        "client_count": Client.objects.count(),
        "site_count": Site.objects.count(),
        "disk_usage_percent": disk_usage,
        "mem_usage_percent": mem_usage,
        "days_until_cert_expires": delta.days,
        "cert_expired": delta.days < 0,
        "redis_ping": redis_ping,
        "celery_queue_len": queue_len,
        "celery_queue_health": celery_queue_health,
        "nats_std_ping": localhost_port_is_open(nats_std_port),
        "nats_ws_ping": localhost_port_is_open(nats_ws_port),
        "mesh_ping": localhost_port_is_open(mesh_port),
        "services_running": {
            "mesh": sysd_svc_is_running("meshcentral.service"),
            "daphne": sysd_svc_is_running("daphne.service"),
            "celery": sysd_svc_is_running("celery.service"),
            "celerybeat": sysd_svc_is_running("celerybeat.service"),
            "redis": sysd_svc_is_running("redis-server.service"),
            "nats": sysd_svc_is_running("nats.service"),
            "nats-api": sysd_svc_is_running("nats-api.service"),
        },
    }

    return JsonResponse(ret, json_dumps_params={"indent": 2})


# TODO deprecated
@csrf_exempt
@monitoring_view
def status(request):
    from agents.models import Agent
    from clients.models import Client, Site

    disk_usage: int = round(psutil.disk_usage("/").percent)
    mem_usage: int = round(psutil.virtual_memory().percent)

    cert_file, _ = get_certs()
    cert_bytes = Path(cert_file).read_bytes()

    cert = x509.load_pem_x509_certificate(cert_bytes)
    delta = cert.not_valid_after_utc - djangotime.now()

    redis_url = f"redis://{settings.REDIS_HOST}"
    redis_ping = False
    with suppress(Exception):
        with from_url(redis_url) as conn:
            conn.ping()
            redis_ping = True

    ret = {
        "version": settings.TRMM_VERSION,
        "latest_agent_version": settings.LATEST_AGENT_VER,
        "agent_count": Agent.objects.count(),
        "client_count": Client.objects.count(),
        "site_count": Site.objects.count(),
        "disk_usage_percent": disk_usage,
        "mem_usage_percent": mem_usage,
        "days_until_cert_expires": delta.days,
        "cert_expired": delta.days < 0,
        "redis_ping": redis_ping,
    }

    if settings.DOCKER_BUILD:
        ret["services_running"] = "not available in docker"
    else:
        ret["services_running"] = {
            "django": sysd_svc_is_running("rmm.service"),
            "mesh": sysd_svc_is_running("meshcentral.service"),
            "daphne": sysd_svc_is_running("daphne.service"),
            "celery": sysd_svc_is_running("celery.service"),
            "celerybeat": sysd_svc_is_running("celerybeat.service"),
            "redis": sysd_svc_is_running("redis-server.service"),
            "postgres": sysd_svc_is_running("postgresql.service"),
            "mongo": sysd_svc_is_running("mongod.service"),
            "nats": sysd_svc_is_running("nats.service"),
            "nats-api": sysd_svc_is_running("nats-api.service"),
            "nginx": sysd_svc_is_running("nginx.service"),
        }
    return JsonResponse(ret, json_dumps_params={"indent": 2})


class OpenAICodeCompletion(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        settings = get_core_settings()

        if not settings.open_ai_token:
            return notify_error(
                "Open AI API Key not found. Open Global Settings > Open AI."
            )

        if not request.data["prompt"]:
            return notify_error("Not prompt field found")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.open_ai_token}",
        }

        data = {
            "messages": [
                {
                    "role": "user",
                    "content": request.data["prompt"],
                },
            ],
            "model": settings.open_ai_model,
            "temperature": 0.5,
            "max_tokens": 1000,
            "n": 1,
            "stop": None,
        }

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                data=json.dumps(data),
            )
        except Exception as e:
            return notify_error(str(e))

        response_data = json.loads(response.text)

        if "error" in response_data:
            return notify_error(
                f"The Open AI API returned an error: {response_data['error']['message']}"
            )

        return Response(response_data["choices"][0]["message"]["content"])


class GetAddAIProvider(APIView):
    permission_classes = [IsAuthenticated, CoreSettingsPerms]

    def get(self, request):
        providers = AIProvider.objects.all().prefetch_related("models")
        return Response(AIProviderSerializer(providers, many=True).data)

    def post(self, request):
        serializer = AIProviderSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("ok")


class UpdateDeleteAIProvider(APIView):
    permission_classes = [IsAuthenticated, CoreSettingsPerms]

    def put(self, request, pk):
        provider = get_object_or_404(AIProvider, pk=pk)
        data = request.data.copy()
        # don't wipe an existing key when the field is left blank on edit
        if not data.get("api_key"):
            data.pop("api_key", None)
        serializer = AIProviderSerializer(instance=provider, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(AIProvider, pk=pk).delete()
        return Response("ok")


class AIAvailableModels(APIView):
    """Ask the pi-trmm-bridge which models are actually available for the
    currently-configured provider API keys."""

    permission_classes = [IsAuthenticated, CoreSettingsPerms]

    def get(self, request):
        import requests as _requests
        from django.conf import settings

        providers = [
            {"name": p.name, "api_key": p.api_key, "base_url": p.base_url}
            for p in AIProvider.objects.filter(enabled=True)
            if p.api_key
        ]
        bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
        try:
            r = _requests.post(
                f"{bridge}/pi/models", json={"providers": providers}, timeout=15
            )
            return Response(r.json())
        except Exception as e:
            return Response({"models": [], "error": str(e)})


class GetAddAIModel(APIView):
    permission_classes = [IsAuthenticated, CoreSettingsPerms]

    def get(self, request):
        models = AIModel.objects.all().select_related("provider")
        return Response(AIModelSerializer(models, many=True).data)

    def post(self, request):
        serializer = AIModelSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("ok")


class UpdateDeleteAIModel(APIView):
    permission_classes = [IsAuthenticated, CoreSettingsPerms]

    def put(self, request, pk):
        model = get_object_or_404(AIModel, pk=pk)
        serializer = AIModelSerializer(instance=model, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(AIModel, pk=pk).delete()
        return Response("ok")


class GetAddAITask(APIView):
    permission_classes = [IsAuthenticated, AITaskPerms]

    def get(self, request):
        from agents.models import Agent

        agent_id = request.query_params.get("agent_id")
        site = request.query_params.get("site")
        client = request.query_params.get("client")
        # only tasks on agents this user's role is allowed to see
        permitted = Agent.objects.filter_by_role(request.user)  # type: ignore
        qs = AITask.objects.select_related("agent", "agent__site", "model").filter(
            agent__in=permitted
        )
        if agent_id:
            qs = qs.filter(agent__agent_id=agent_id)
        elif site:
            qs = qs.filter(agent__site_id=site)
        elif client:
            qs = qs.filter(agent__site__client_id=client)
        return Response(AITaskSerializer(qs.order_by("agent__hostname", "name"), many=True).data)

    def post(self, request):
        from agents.models import Agent

        data = request.data.copy()
        agent_id = data.pop("agent_id", None)
        if agent_id:
            if isinstance(agent_id, list):
                agent_id = agent_id[0]
            agent = get_object_or_404(Agent, agent_id=agent_id)
            if not _has_perm_on_agent(request.user, agent.agent_id):
                raise PermissionDenied()
            data["agent"] = agent.pk
        serializer = AITaskSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        _apply_once_schedule(obj)
        return Response("ok")


def _apply_once_schedule(task):
    """Arm a task's next execution: run_at for one-time, next_run for recurring
    scheduled, or neither for on-demand 'now' tasks."""
    import datetime as _dt

    from django.utils import timezone as _tz

    from core.tasks import _compute_task_next_run

    if task.schedule_type == AITask.SCHEDULE_ONCE:
        if task.run_time:
            now = _tz.localtime()
            target = now.replace(
                hour=task.run_time.hour,
                minute=task.run_time.minute,
                second=0,
                microsecond=0,
            )
            if target <= now:
                target += _dt.timedelta(days=1)
            task.run_at = target
        task.next_run = None
    elif task.run_mode == "now":
        task.run_at = None
        task.next_run = None
    else:  # recurring scheduled (interval/daily/weekly/monthly)
        task.run_at = None
        task.next_run = _compute_task_next_run(task)
    task.save(update_fields=["run_at", "next_run"])


class UpdateDeleteAITask(APIView):
    permission_classes = [IsAuthenticated, AITaskPerms]

    def put(self, request, pk):
        task = get_object_or_404(AITask.objects.select_related("agent"), pk=pk)
        if not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()
        serializer = AITaskSerializer(instance=task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        _apply_once_schedule(obj)
        return Response("ok")

    def delete(self, request, pk):
        task = get_object_or_404(AITask.objects.select_related("agent"), pk=pk)
        if not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()
        task.delete()
        return Response("ok")


class RunAITaskNow(APIView):
    permission_classes = [IsAuthenticated, AITaskPerms]

    def post(self, request, pk):
        from core.tasks import run_ai_task

        task = get_object_or_404(AITask.objects.select_related("agent"), pk=pk)
        if not _has_perm_on_agent(request.user, task.agent.agent_id):
            raise PermissionDenied()
        run_ai_task.delay(pk, triggered_by="manual")
        return Response("Task queued to run now")


class AITaskRuns(APIView):
    """List run history for a task, or all recent runs for an agent."""

    permission_classes = [IsAuthenticated, AITaskPerms]

    def get(self, request):
        from django.db.models import Q
        from agents.models import Agent

        permitted = Agent.objects.filter_by_role(request.user)  # type: ignore
        # runs belong to a task (task.agent) or a bulk command (agent set directly)
        qs = AITaskRun.objects.select_related(
            "task", "task__agent", "bulk", "agent"
        ).filter(Q(agent__in=permitted) | Q(task__agent__in=permitted))
        task_id = request.query_params.get("task_id")
        bulk_id = request.query_params.get("bulk_id")
        agent_id = request.query_params.get("agent_id")
        if task_id:
            qs = qs.filter(task_id=task_id)
        elif bulk_id:
            qs = qs.filter(bulk_id=bulk_id)
        elif agent_id:
            qs = qs.filter(
                Q(agent__agent_id=agent_id) | Q(task__agent__agent_id=agent_id)
            )
        return Response(AITaskRunSerializer(qs[:200], many=True).data)


class AITaskRunLive(APIView):
    """Return live progress for an in-flight run (from redis, written by the
    bridge), falling back to the persisted run record when finished."""

    permission_classes = [IsAuthenticated, AITaskPerms]

    def get(self, request, run_id):
        import json as _json

        from redis import from_url

        live = None
        try:
            with from_url(
                f"redis://{settings.REDIS_HOST}:6379", decode_responses=True
            ) as conn:
                raw = conn.get(f"pi_run:{run_id}")
            if raw:
                live = _json.loads(raw)
        except Exception:
            live = None

        run = AITaskRun.objects.select_related("task__agent", "agent").filter(
            run_id=run_id
        ).first()
        # only expose runs on agents this user is allowed to see
        run_agent = run.get_agent() if run else None
        if run_agent and not _has_perm_on_agent(request.user, run_agent.agent_id):
            raise PermissionDenied()
        return Response(
            {
                "live": live,
                "run": AITaskRunSerializer(run).data if run else None,
            }
        )


class AISendEmail(APIView):
    """Send a plain-text email through the RMM server's configured SMTP.

    Called by the pi-trmm-bridge (X-API-KEY service auth) on behalf of the AI
    assistant (chat or scheduled AI task) when the operator asks for results
    to be emailed. Uses the exact same SMTP settings as TRMM alerting.
    """

    permission_classes = [IsAuthenticated]

    MAX_RECIPIENTS = 10
    MAX_SUBJECT = 200
    MAX_BODY = 100_000

    def post(self, request):
        from django.core.exceptions import ValidationError
        from django.core.validators import validate_email

        from logs.models import DebugLog

        core = get_core_settings()
        if not core.ai_module_enabled:
            return notify_error("AI module is disabled.")
        if not core.email_is_configured:
            return notify_error(
                "SMTP is not configured in TRMM global settings (Settings > Global Settings > Email Alerts)."
            )

        raw_to = request.data.get("to") or ""
        if isinstance(raw_to, str):
            recipients = [
                e.strip()
                for e in raw_to.replace(";", ",").split(",")
                if e.strip()
            ]
        elif isinstance(raw_to, list):
            recipients = [str(e).strip() for e in raw_to if str(e).strip()]
        else:
            recipients = []

        if not recipients or len(recipients) > self.MAX_RECIPIENTS:
            return notify_error(
                f"Provide between 1 and {self.MAX_RECIPIENTS} recipient email addresses."
            )
        for e in recipients:
            try:
                validate_email(e)
            except ValidationError:
                return notify_error(f"Invalid email address: {e}")

        subject = str(request.data.get("subject") or "").strip()[: self.MAX_SUBJECT]
        body = str(request.data.get("body") or "")[: self.MAX_BODY]
        if not subject or not body:
            return notify_error("Both subject and body are required.")

        # ---- From address -------------------------------------------------
        # Rules:
        #  - full address given (has '@')  -> used verbatim ("whatever we want")
        #  - local part only given         -> <localpart>@<smtp domain>
        #  - nothing given                 -> pi-<job_ref|random>@<smtp domain>
        # The domain always defaults to the SMTP from-address domain so mail
        # stays aligned with the configured/authorized sending domain.
        import re
        import secrets

        smtp_domain = (core.smtp_from_email or "").split("@")[-1].strip()
        raw_from = str(request.data.get("from_address") or "").strip()
        from_name = request.data.get("from_name")
        if from_name is not None:
            from_name = str(from_name)[:120]

        if raw_from and "@" in raw_from:
            from_address = raw_from
        else:
            if raw_from:
                local = raw_from
            else:
                job_ref = str(request.data.get("job_ref") or "").strip()
                base = job_ref or secrets.token_hex(4)
                local = f"pi-{base}"
            # sanitize local part to valid email-local characters
            local = re.sub(r"[^A-Za-z0-9._+-]", "", local)[:64] or f"pi-{secrets.token_hex(4)}"
            if not smtp_domain:
                return notify_error(
                    "SMTP from-address has no domain configured; cannot build a From address."
                )
            from_address = f"{local}@{smtp_domain}"

        try:
            validate_email(from_address)
        except ValidationError:
            return notify_error(f"Invalid From address: {from_address}")

        # test=True makes send_mail return the REAL smtp error on failure
        # (with test=False it always returns ok); behavior is otherwise identical.
        msg, ok = core.send_mail(
            subject,
            body,
            override_recipients=recipients,
            override_from=from_address,
            override_from_name=from_name,
            test=True,
        )
        if not ok:
            return notify_error(f"Email send failed: {msg}")

        DebugLog.info(
            message=f"AI assistant sent email to {', '.join(recipients)} from {from_address}: "
            f"{subject} (requested by {request.user.username})"
        )
        return Response(
            {
                "ok": True,
                "detail": f"Email sent to {', '.join(recipients)} from {from_address}",
            }
        )


class GetAddBulkAICommand(APIView):
    permission_classes = [IsAuthenticated, BulkAIPerms]

    def get(self, request):
        cmds = BulkAICommand.objects.select_related("model", "client", "site").prefetch_related("agents")
        return Response(BulkAICommandSerializer(cmds, many=True).data)

    def post(self, request):
        from agents.models import Agent
        from tacticalrmm.permissions import _has_perm_on_client, _has_perm_on_site

        data = request.data.copy()
        agent_ids = data.pop("agent_ids", None) or []
        if isinstance(agent_ids, str):
            agent_ids = [agent_ids]
        # validate target access (mirrors bulk command)
        if data.get("target") == "client" and data.get("client"):
            if not _has_perm_on_client(request.user, data["client"]):
                raise PermissionDenied()
        elif data.get("target") == "site" and data.get("site"):
            if not _has_perm_on_site(request.user, data["site"]):
                raise PermissionDenied()

        serializer = BulkAICommandSerializer(data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        cmd = serializer.save()
        if agent_ids:
            cmd.agents.set(Agent.objects.filter(agent_id__in=agent_ids))
        _arm_bulk_next_run(cmd)
        return Response("ok")


def _arm_bulk_next_run(cmd):
    from core.tasks import _compute_bulk_next_run

    # only recurring commands get a next_run; "now" ones run on demand
    cmd.next_run = (
        _compute_bulk_next_run(cmd) if cmd.run_mode == "schedule" else None
    )
    cmd.save(update_fields=["next_run"])


class UpdateDeleteBulkAICommand(APIView):
    permission_classes = [IsAuthenticated, BulkAIPerms]

    def put(self, request, pk):
        from agents.models import Agent

        cmd = get_object_or_404(BulkAICommand, pk=pk)
        data = request.data.copy()
        agent_ids = data.pop("agent_ids", None)
        serializer = BulkAICommandSerializer(instance=cmd, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        cmd = serializer.save()
        if agent_ids is not None:
            cmd.agents.set(Agent.objects.filter(agent_id__in=agent_ids))
        _arm_bulk_next_run(cmd)
        return Response("ok")

    def delete(self, request, pk):
        get_object_or_404(BulkAICommand, pk=pk).delete()
        return Response("ok")


class RunBulkAICommandNow(APIView):
    permission_classes = [IsAuthenticated, BulkAIPerms]

    def post(self, request, pk):
        from core.tasks import run_bulk_ai_command

        get_object_or_404(BulkAICommand, pk=pk)
        run_bulk_ai_command.delay(pk, triggered_by="manual")
        return Response("Bulk AI command queued to run now")


class BulkAICommandResults(APIView):
    """Latest run per agent for one bulk command (computers-left / results-right
    viewer). Scoped to the agents the caller may see."""

    permission_classes = [IsAuthenticated, BulkAIPerms]

    def get(self, request, pk):
        from agents.models import Agent

        get_object_or_404(BulkAICommand, pk=pk)
        permitted = Agent.objects.filter_by_role(request.user)  # type: ignore
        runs = (
            AITaskRun.objects.filter(bulk_id=pk, agent__in=permitted)
            .select_related("agent__site__client")
            .order_by("agent_id", "-started_at")
        )
        seen = set()
        latest = []
        for r in runs:
            if r.agent_id in seen:
                continue
            seen.add(r.agent_id)
            latest.append(r)
        latest.sort(key=lambda r: (r.agent.hostname.lower() if r.agent else ""))
        return Response(AITaskRunSerializer(latest, many=True).data)


def _revoke_ai_agent_tasks(cmd_id=None):
    """Revoke (terminate) queued/active Celery AI runner tasks. If cmd_id is
    given, only tasks for that bulk command; otherwise all AI runner tasks.
    Returns the number of tasks revoked."""
    from tacticalrmm.celery import app

    names = (
        "run_bulk_ai_agent",
        "run_bulk_ai_command",
        "run_ai_task",
    )
    revoked = 0
    try:
        insp = app.control.inspect(timeout=8)
        buckets = []
        for getter in (insp.active, insp.reserved, insp.scheduled):
            try:
                buckets.append(getter() or {})
            except Exception:
                pass
        for bucket in buckets:
            for _worker, tasks in bucket.items():
                for t in tasks:
                    tname = t.get("name", "") or ""
                    if not any(tname.endswith(n) for n in names):
                        continue
                    if cmd_id is not None:
                        args = t.get("args") or []
                        # run_bulk_ai_agent(cmd_id, agent_pk, ...) / run_bulk_ai_command(cmd_id)
                        if not (isinstance(args, list) and args and args[0] == cmd_id):
                            continue
                    app.control.revoke(t["id"], terminate=True, signal="SIGTERM")
                    revoked += 1
    except Exception:
        pass
    return revoked


def _abort_bridge_runs(run_ids=None, all_runs=False):
    """Tell the bridge to abort in-flight headless runs (stops LLM spend)."""
    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    payload = {"all": True} if all_runs else {"run_ids": list(run_ids or [])}
    try:
        r = requests.post(f"{bridge}/pi/run/abort", json=payload, timeout=15)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


class StopBulkAICommand(APIView):
    """Kill switch for one bulk AI command: disable it, revoke its queued/active
    Celery tasks, abort its in-flight bridge runs, and mark running rows stopped."""

    permission_classes = [IsAuthenticated, BulkAIPerms]

    def post(self, request, pk):
        from core.tasks import cmd_stop_set

        cmd = get_object_or_404(BulkAICommand, pk=pk)
        # 1) stop it from (re)dispatching
        cmd.enabled = False
        cmd.next_run = None
        cmd.save(update_fields=["enabled", "next_run"])
        # set the per-command stop flag so any queued backlog no-ops on execute
        cmd_stop_set(pk)
        # 2) revoke queued/active celery runner tasks for this command
        revoked = _revoke_ai_agent_tasks(cmd_id=pk)
        # 3) abort in-flight bridge runs + mark rows stopped
        running = AITaskRun.objects.filter(bulk_id=pk, status="running")
        run_ids = list(running.values_list("run_id", flat=True))
        bridge = _abort_bridge_runs(run_ids=run_ids)
        stopped = running.update(
            status="error",
            summary="Stopped by operator",
            finished_at=djangotime.now(),
        )
        return Response(
            {
                "detail": f"Stopped '{cmd.name}': disabled, {revoked} queued tasks revoked, "
                f"{bridge.get('aborted', 0)} live runs aborted, {stopped} rows marked stopped.",
                "revoked": revoked,
                "aborted": bridge.get("aborted", 0),
                "stopped": stopped,
            }
        )


class StopAllAIRuns(APIView):
    """Emergency stop: abort ALL in-flight AI runs (bulk + scheduled) and revoke
    all queued AI runner tasks. Does NOT disable schedules (use per-command stop
    for that) - purely halts current spend."""

    permission_classes = [IsAuthenticated, BulkAIPerms]

    def post(self, request):
        from core.tasks import ai_kill_set

        # set the global kill flag first so any queued backlog no-ops on execute
        ai_kill_set(seconds=900)
        revoked = _revoke_ai_agent_tasks(cmd_id=None)
        bridge = _abort_bridge_runs(all_runs=True)
        stopped = AITaskRun.objects.filter(status="running").update(
            status="error",
            summary="Stopped by operator (emergency stop)",
            finished_at=djangotime.now(),
        )
        return Response(
            {
                "detail": f"Emergency stop: {revoked} queued tasks revoked, "
                f"{bridge.get('aborted', 0)} live runs aborted, {stopped} rows marked stopped.",
                "revoked": revoked,
                "aborted": bridge.get("aborted", 0),
                "stopped": stopped,
            }
        )


class PreviewBulkAITargets(APIView):
    """Return how many/which online agents a target selection would hit."""

    permission_classes = [IsAuthenticated, BulkAIPerms]

    def post(self, request):
        from core.tasks import _resolve_bulk_targets

        class _Tmp:
            pass

        tmp = _Tmp()
        tmp.target = request.data.get("target", "all")
        tmp.client_id = request.data.get("client")
        tmp.site_id = request.data.get("site")
        tmp.mon_type = request.data.get("mon_type", "all")
        tmp.os_type = request.data.get("os_type", "all")
        tmp.filters = request.data.get("filters") or []
        tmp.filter_match = request.data.get("filter_match", "any")
        # resolve the FULL matched set (ignore exclusions) so the UI can show
        # every match with an exclude checkbox; we mark/count exclusions below.
        tmp.exclude_agent_ids = []
        exclude_ids = set(request.data.get("exclude_agent_ids") or [])

        agent_ids = request.data.get("agent_ids") or []

        class _AgentsProxy:
            def values_list(self, *a, **k):
                from agents.models import Agent

                return Agent.objects.filter(agent_id__in=agent_ids).values_list("pk", flat=True)

        tmp.agents = _AgentsProxy()
        agents = _resolve_bulk_targets(tmp)
        from core.tasks import _bulk_max_agents

        cap = _bulk_max_agents()
        effective = [a for a in agents if a.agent_id not in exclude_ids]
        return Response(
            {
                "online_count": len(effective),  # after exclusions (what will run)
                "matched_count": len(agents),  # before exclusions
                "excluded_count": len(agents) - len(effective),
                "cap": cap,
                "over_cap": len(effective) > cap,
                "agents": [
                    {
                        "agent_id": a.agent_id,
                        "hostname": a.hostname,
                        "client": a.client.name,
                        "site": a.site.name,
                        "excluded": a.agent_id in exclude_ids,
                    }
                    for a in agents[:500]
                ],
            }
        )
