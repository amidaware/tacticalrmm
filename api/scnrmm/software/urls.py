from django.urls import path

from . import views

urlpatterns = [
    path("chocos/", views.chocos),
    path("", views.GetSoftware.as_view()),
    path("<agent:agent_id>/", views.GetSoftware.as_view()),
]
