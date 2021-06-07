from django.urls import path

from . import views

urlpatterns = [
    path("checks/", views.AddCheck.as_view()),
    path("<int:pk>/check/", views.GetUpdateDeleteCheck.as_view()),
    path("<pk>/loadchecks/", views.load_checks),
    path("getalldisks/", views.get_disks_for_policies),
    path("runchecks/<pk>/", views.run_checks),
    path("history/<int:checkpk>/", views.GetCheckHistory.as_view()),
]
