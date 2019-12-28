from django.contrib import admin
from django.urls import path, include
from knox import views as knox_views
from accounts.views import LoginView, installer_twofactor

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", LoginView.as_view()),
    path("logout/", knox_views.LogoutView.as_view()),
    path("logoutall/", knox_views.LogoutAllView.as_view()),
    path("installer/twofactor/", installer_twofactor),
    path("api/v1/", include("api.urls")),
    path("clients/", include("clients.urls")),
    path("agents/", include("agents.urls")),
    path("checks/", include("checks.urls")),
    path("services/", include("services.urls")),
    path("winupdate/", include("winupdate.urls")),
]
