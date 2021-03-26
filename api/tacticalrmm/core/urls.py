from django.urls import path

from . import views

urlpatterns = [
    path("uploadmesh/", views.UploadMeshAgent.as_view()),
    path("getcoresettings/", views.get_core_settings),
    path("editsettings/", views.edit_settings),
    path("version/", views.version),
    path("emailtest/", views.email_test),
    path("dashinfo/", views.dashboard_info),
    path("servermaintenance/", views.server_maintenance),
    path("customfields/", views.GetAddCustomFields.as_view()),
    path("customfields/<int:pk>/", views.GetUpdateDeleteCustomFields.as_view()),
]
