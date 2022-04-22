from django.urls import path

from . import views

urlpatterns = [
    path("settings/", views.GetEditCoreSettings.as_view()),
    path("version/", views.version),
    path("emailtest/", views.email_test),
    path("dashinfo/", views.dashboard_info),
    path("servermaintenance/", views.server_maintenance),
    path("customfields/", views.GetAddCustomFields.as_view()),
    path("customfields/<int:pk>/", views.GetUpdateDeleteCustomFields.as_view()),
    path("codesign/", views.CodeSign.as_view()),
    path("keystore/", views.GetAddKeyStore.as_view()),
    path("keystore/<int:pk>/", views.UpdateDeleteKeyStore.as_view()),
    path("urlaction/", views.GetAddURLAction.as_view()),
    path("urlaction/<int:pk>/", views.UpdateDeleteURLAction.as_view()),
    path("urlaction/run/", views.RunURLAction.as_view()),
    path("smstest/", views.TwilioSMSTest.as_view()),
    path("clearcache/", views.clear_cache),
]
