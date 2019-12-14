from django.urls import path
from . import views

urlpatterns = [
    path("<pk>/getwinupdates/", views.get_win_updates),
    path("<pk>/runupdatescan/", views.run_update_scan),
    path("editpolicy/", views.edit_policy),
    path("winupdater/", views.win_updater),
    path("results/", views.results),
]