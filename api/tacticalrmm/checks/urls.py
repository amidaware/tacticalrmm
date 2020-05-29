from django.urls import path
from . import views

urlpatterns = [
    path("checks/", views.GetAddCheck.as_view()),
    path("<int:pk>/check/", views.GetUpdateDeleteCheck.as_view()),
    path("<pk>/loadchecks/", views.load_checks),
    path("checkrunner/", views.check_runner),
    path("getalldisks/", views.get_disks_for_policies),
    path("runchecks/<pk>/", views.run_checks),
    path("checkresults/", views.check_results),
]
