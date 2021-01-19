from django.urls import path
from . import views

urlpatterns = [
    path("natsinfo/", views.nats_info),
    path("checkin/", views.NatsCheckIn.as_view()),
    path("syncmesh/", views.SyncMeshNodeID.as_view()),
    path("winupdates/", views.NatsWinUpdates.as_view()),
    path("choco/", views.NatsChoco.as_view()),
]
