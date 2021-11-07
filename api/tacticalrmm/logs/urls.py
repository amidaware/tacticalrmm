from django.urls import path

from . import views

urlpatterns = [
    path("pendingactions/", views.PendingActions.as_view()),
    path("pendingactions/<int:pk>/", views.PendingActions.as_view()),
    path("audit/", views.GetAuditLogs.as_view()),
    path("debug/", views.GetDebugLog.as_view()),
]
