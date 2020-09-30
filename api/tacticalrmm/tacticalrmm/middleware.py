from django.db.models import signals
from django.conf import settings
from functools import partial
from tacticalrmm.utils import get_random_string
from logs.models import AuditLog

# Audited Models
from automation.models import Policy
from agents.models import Agent
from checks.models import Check
from autotasks.models import AutomatedTask
from winupdate.models import WinUpdatePolicy
from clients.models import Client, Site
from accounts.models import User
from scripts.models import Script
from core.models import CoreSettings

audit_models = (
    Policy,
    Agent,
    Check,
    AutomatedTask,
    WinUpdatePolicy,
    Client,
    Site,
    User,
    Script,
    CoreSettings,
)

EXCLUDE_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")

# these routes are stricly called only by agents
EXCLUDE_PATHS = (
    "/api/v2",
    "/api/v1",
    "/logs/auditlogs",
    "/winupdate/winupdater",
    "/winupdate/results",
    f"/{settings.ADMIN_URL}",
    "/logout",
)


class AuditMiddleware:

    before_value = {}
    debug_info = {}
    pre_save_uid = ""
    post_save_uid = ""
    pre_delete_uid = ""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)

        # disconnect signals
        signals.pre_save.disconnect(dispatch_uid=self.pre_save_uid)
        signals.post_save.disconnect(dispatch_uid=self.post_save_uid)
        signals.pre_delete.disconnect(dispatch_uid=self.pre_delete_uid)

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method not in EXCLUDE_METHODS and not request.path.startswith(
            EXCLUDE_PATHS
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
                # Can't initialize the request from this view. Fallback to using default permission classes
                request = APIView().initialize_request(request)

            # check if user is authenticated
            if hasattr(request, "user") and request.user.is_authenticated:

                self.pre_save_uid = get_random_string(8)
                self.post_save_uid = get_random_string(8)
                self.pre_delete_uid = get_random_string(8)

                # gather and save debug info
                self.debug_info["url"] = request.path
                self.debug_info["method"] = request.method
                self.debug_info["view_class"] = view_func.cls.__name__
                self.debug_info["view_func"] = view_func.__name__
                self.debug_info["view_args"] = view_args
                self.debug_info["view_kwargs"] = view_kwargs

                # get authentcated user after request
                user = request.user
                # sets the created_by and modified_by fields on models
                pre_save_audit = partial(self.pre_save_audit, user)
                signals.pre_save.connect(
                    pre_save_audit, dispatch_uid=self.pre_save_uid, weak=False
                )

                # adds audit entry for adds and changes to models
                add_audit_entry_add_modify = partial(
                    self.add_audit_entry_add_modify, user
                )
                signals.post_save.connect(
                    add_audit_entry_add_modify,
                    dispatch_uid=self.post_save_uid,
                    weak=False,
                )

                # adds audit entry for deletes to models
                add_audit_entry_delete = partial(self.add_audit_entry_delete, user)
                signals.pre_delete.connect(
                    add_audit_entry_delete, dispatch_uid=self.pre_delete_uid, weak=False
                )

    def pre_save_audit(self, user, sender, instance, **kwargs):

        # populate created_by and modified_by fields on instance
        if not getattr(instance, "created_by", None):
            instance.created_by = user.username
        if hasattr(instance, "modified_by"):
            instance.modified_by = user.username

        # capture object properties before edit
        if sender in audit_models:
            if instance.id:
                self.before_value = sender.objects.get(pk=instance.id)

    def add_audit_entry_add_modify(self, user, sender, instance, created, **kwargs):

        # check and see if sender is an auditable instance
        if sender in audit_models:
            if created:
                AuditLog.audit_object_add(
                    user.username,
                    sender.__name__.lower(),
                    sender.serialize(instance),
                    instance.__str__(),
                    debug_info=self.debug_info,
                )
            else:
                AuditLog.audit_object_changed(
                    user.username,
                    sender.__name__.lower(),
                    sender.serialize(self.before_value),
                    sender.serialize(instance),
                    instance.__str__(),
                    debug_info=self.debug_info,
                )

    def add_audit_entry_delete(self, user, sender, instance, **kwargs):

        # check and see if sender is an auditable instance
        if sender in audit_models:
            AuditLog.audit_object_delete(
                user.username,
                sender.__name__.lower(),
                sender.serialize(instance),
                instance.__str__(),
                debug_info=self.debug_info,
            )
