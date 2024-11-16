from django.conf import settings
from django.urls import include, path, register_converter
from knox import views as knox_views

from accounts.views import CheckCredsV2, LoginViewV2
from ee.sso.urls import allauth_urls

# from agents.consumers import SendCMD
from core.consumers import DashInfo, TerminalConsumer
from core.views import home


class AgentIDConverter:
    regex = "[^/]{20}[^/]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(AgentIDConverter, "agent")

urlpatterns = [
    path("", home),
    path("v2/checkcreds/", CheckCredsV2.as_view()),
    path("v2/login/", LoginViewV2.as_view()),
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
    path("reporting/", include("ee.reporting.urls")),
]

if not getattr(settings, "TRMM_DISABLE_SSO", False):
    urlpatterns += (
        path("_allauth/", include(allauth_urls)),
        path("accounts/", include("ee.sso.urls")),
    )

if getattr(settings, "BETA_API_ENABLED", False):
    urlpatterns += (path("beta/v1/", include("beta.v1.urls")),)

if getattr(settings, "ADMIN_ENABLED", False):
    from django.contrib import admin

    urlpatterns += (path(settings.ADMIN_URL, admin.site.urls),)

if getattr(settings, "DEBUG", False) and not getattr(settings, "DEMO", False):
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
    path("ws/dashinfo/", DashInfo.as_asgi()),
    # path("ws/sendcmd/", SendCMD.as_asgi()),
]

if not (
    getattr(settings, "HOSTED", False)
    or getattr(settings, "TRMM_DISABLE_WEB_TERMINAL", False)
    or getattr(settings, "DEMO", False)
):
    ws_urlpatterns += [
        path("ws/trmmcli/", TerminalConsumer.as_asgi()),
    ]
