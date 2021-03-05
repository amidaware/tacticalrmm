from django.urls import path

from . import views

urlpatterns = [
    path("policies/", views.GetAddPolicies.as_view()),
    path("policies/<int:pk>/related/", views.GetRelated.as_view()),
    path("policies/overview/", views.OverviewPolicy.as_view()),
    path("policies/<int:pk>/", views.GetUpdateDeletePolicy.as_view()),
    path("sync/", views.PolicySync.as_view()),
    path("<int:pk>/policychecks/", views.PolicyCheck.as_view()),
    path("<int:pk>/policyautomatedtasks/", views.PolicyAutoTask.as_view()),
    path("policycheckstatus/<int:check>/check/", views.PolicyCheck.as_view()),
    path("policyautomatedtaskstatus/<int:task>/task/", views.PolicyAutoTask.as_view()),
    path("runwintask/<int:task>/", views.PolicyAutoTask.as_view()),
    path("winupdatepolicy/", views.UpdatePatchPolicy.as_view()),
    path("winupdatepolicy/<int:patchpolicy>/", views.UpdatePatchPolicy.as_view()),
    path("winupdatepolicy/reset/", views.UpdatePatchPolicy.as_view()),
]
