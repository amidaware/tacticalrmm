from django.urls import path

from . import views

urlpatterns = [
    path("<int:pk>/automatedtasks/", views.AutoTask.as_view()),
    path("automatedtasks/", views.AddAutoTask.as_view()),
    path("runwintask/<int:pk>/", views.run_task),
]
