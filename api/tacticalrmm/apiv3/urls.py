from django.urls import path

from . import views

urlpatterns = [
    path("checkrunner/", views.CheckRunner.as_view()),
    path("<str:agentid>/checkrunner/", views.CheckRunner.as_view()),
    path("<str:agentid>/runchecks/", views.RunChecks.as_view()),
    path("<str:agentid>/checkinterval/", views.CheckRunnerInterval.as_view()),
    path("<int:pk>/<str:agentid>/taskrunner/", views.TaskRunner.as_view()),
    path("meshexe/", views.MeshExe.as_view()),
    path("newagent/", views.NewAgent.as_view()),
    path("software/", views.Software.as_view()),
    path("installer/", views.Installer.as_view()),
    path("checkin/", views.CheckIn.as_view()),
    path("syncmesh/", views.SyncMeshNodeID.as_view()),
    path("choco/", views.Choco.as_view()),
    path("winupdates/", views.WinUpdates.as_view()),
    path("superseded/", views.SupersededWinUpdate.as_view()),
    path("<int:pk>/chocoresult/", views.ChocoResult.as_view()),
    path("<int:pk>/<str:agentid>/histresult/", views.AgentHistoryResult.as_view()),
    path("<str:agentid>/config/", views.AgentConfig.as_view()),
]
