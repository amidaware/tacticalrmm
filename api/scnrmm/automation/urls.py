from django.urls import path

from autotasks.views import GetAddAutoTasks
from checks.views import GetAddChecks

from . import views

urlpatterns = [
    path("policies/", views.GetAddPolicies.as_view()),
    path("policies/<int:pk>/related/", views.GetRelated.as_view()),
    path("policies/overview/", views.OverviewPolicy.as_view()),
    path("policies/<int:pk>/", views.GetUpdateDeletePolicy.as_view()),
    # alias to get policy checks
    path("policies/<int:policy>/checks/", GetAddChecks.as_view()),
    # alias to get policy tasks
    path("policies/<int:policy>/tasks/", GetAddAutoTasks.as_view()),
    path("checks/<int:check>/status/", views.PolicyCheck.as_view()),
    path("tasks/<int:task>/status/", views.PolicyAutoTask.as_view()),
    path("tasks/<int:task>/run/", views.PolicyAutoTask.as_view()),
    path("patchpolicy/", views.UpdatePatchPolicy.as_view()),
    path("patchpolicy/<int:pk>/", views.UpdatePatchPolicy.as_view()),
    path("patchpolicy/reset/", views.ResetPatchPolicy.as_view()),
]
