from django.urls import path
from . import views

urlpatterns = [
    path("policies/", views.GetAddPolicies.as_view()),
    path("policies/<pk>/", views.GetAddDeletePolicy.as_view()),
    path("<int:pk>/automatedtasks/", views.AutoTask.as_view()),
    path("taskrunner/<int:pk>/", views.TaskRunner.as_view()),
    path("runwintask/<int:pk>/", views.run_task),
]
