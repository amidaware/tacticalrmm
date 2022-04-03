from accounts.views import CheckCreds, LoginView
from core.consumers import DashInfo
from django.conf import settings
from django.urls import include, path, register_converter
from knox import views as knox_views


class AgentIDConverter:
    regex = "[^/]{20}[^/]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(AgentIDConverter, "agent")

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

if getattr(settings, "ADMIN_ENABLED", False):
    from django.contrib import admin

    urlpatterns += (path(settings.ADMIN_URL, admin.site.urls),)

if getattr(settings, "DEBUG", False):
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

if getattr(settings, "SWAGGER_ENABLED", False):
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += (
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    )

ws_urlpatterns = [
    path("ws/dashinfo/", DashInfo.as_asgi()),  # type: ignore
]
