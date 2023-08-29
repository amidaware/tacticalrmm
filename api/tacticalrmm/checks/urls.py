from django.urls import path

from . import views

urlpatterns = [
    path("", views.GetAddChecks.as_view()),
    path("<int:pk>/", views.GetUpdateDeleteCheck.as_view()),
    path("<int:pk>/reset/", views.ResetCheck.as_view()),
    path("<agent:agent_id>/resetall/", views.ResetAllChecksStatus.as_view()),
    path("<agent:agent_id>/run/", views.run_checks),
    path("<int:pk>/history/", views.GetCheckHistory.as_view()),
    path("<str:target>/<int:pk>/csbulkrun/", views.bulk_run_checks),
]
