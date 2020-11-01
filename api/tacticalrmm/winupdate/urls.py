from django.urls import path
from . import views
from apiv3 import views as v3_views

urlpatterns = [
    path("<int:pk>/getwinupdates/", views.get_win_updates),
    path("<int:pk>/runupdatescan/", views.run_update_scan),
    path("editpolicy/", views.edit_policy),
    path("winupdater/", views.win_updater),
    path("results/", v3_views.WinUpdater.as_view()),
    path("<int:pk>/installnow/", views.install_updates),
]
