from django.urls import path

from . import views

urlpatterns = [
    path("pendingactions/", views.PendingActions.as_view()),
    path("auditlogs/", views.GetAuditLogs.as_view()),
    path("auditlogs/optionsfilter/", views.FilterOptionsAuditLog.as_view()),
    path("debuglog/", views.GetDebugLog.as_view()),
]
