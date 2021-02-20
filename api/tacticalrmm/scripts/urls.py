from django.urls import path

from . import views

urlpatterns = [
    path("scripts/", views.GetAddScripts.as_view()),
    path("<int:pk>/script/", views.GetUpdateDeleteScript.as_view()),
    path("<int:pk>/download/", views.download),
]
