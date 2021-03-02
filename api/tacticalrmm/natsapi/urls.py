from django.urls import path

from . import views

urlpatterns = [
    path("natsinfo/", views.nats_info),
    path("<str:stat>/agents/", views.NatsAgents.as_view()),
    path("logcrash/", views.LogCrash.as_view()),
]
