from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from knox import views as knox_views
from accounts.views import LoginView, CheckCreds

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("checkcreds/", CheckCreds.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", knox_views.LogoutView.as_view()),
    path("logoutall/", knox_views.LogoutAllView.as_view()),
    path("api/v1/", include("api.urls")),
    path("api/v2/", include("apiv2.urls")),
    path("api/v3/", include("apiv3.urls")),
    path("clients/", include("clients.urls")),
    path("agents/", include("agents.urls")),
    path("checks/", include("checks.urls")),
    path("services/", include("services.urls")),
    path("winupdate/", include("winupdate.urls")),
    path("software/", include("software.urls")),
    path("core/", include("core.urls")),
    path("automation/", include("automation.urls")),
    path("tasks/", include("autotasks.urls")),
    path("logs/", include("logs.urls")),
    path("scripts/", include("scripts.urls")),
    path("alerts/", include("alerts.urls")),
    path("accounts/", include("accounts.urls")),
]
