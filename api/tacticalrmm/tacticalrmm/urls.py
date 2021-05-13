from django.conf import settings
from django.urls import include, path
from knox import views as knox_views

from accounts.views import CheckCreds, LoginView
from core.consumers import DashInfo

urlpatterns = [
    path("checkcreds/", CheckCreds.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", knox_views.LogoutView.as_view()),
    path("logoutall/", knox_views.LogoutAllView.as_view()),
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

if hasattr(settings, "ADMIN_ENABLED") and settings.ADMIN_ENABLED:
    from django.contrib import admin

    urlpatterns += (path(settings.ADMIN_URL, admin.site.urls),)

ws_urlpatterns = [
    path("ws/dashinfo/", DashInfo.as_asgi()),  # type: ignore
]
