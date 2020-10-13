from django.urls import path
from . import views

urlpatterns = [
    path("checkrunner/", views.CheckRunner.as_view()),
    path("<str:agentid>/checkrunner/", views.CheckRunner.as_view()),
]
