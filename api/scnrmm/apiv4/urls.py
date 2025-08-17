from django.urls import path

from . import views

urlpatterns = [
    path("<str:agentid>/<int:pk>/chocoresult/", views.ChocoResultV4.as_view()),
]
