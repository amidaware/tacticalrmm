from django.urls import path

from . import views

urlpatterns = [
    path("", views.GetAddAutoTasks.as_view()),
    path("<int:pk>/", views.GetEditDeleteAutoTask.as_view()),
    path("<int:pk>/run/", views.RunAutoTask.as_view()),
]
