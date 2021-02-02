from django.urls import path
from . import views

urlpatterns = [
    path("natsinfo/", views.nats_info),
    path("checkin/", views.NatsCheckIn.as_view()),
    path("syncmesh/", views.SyncMeshNodeID.as_view()),
    path("winupdates/", views.NatsWinUpdates.as_view()),
    path("choco/", views.NatsChoco.as_view()),
    path("wmi/", views.NatsWMI.as_view()),
    path("offline/", views.OfflineAgents.as_view()),
    path("logcrash/", views.LogCrash.as_view()),
    path("superseded/", views.SupersededWinUpdate.as_view()),
]
