from django.urls import path
from . import views

urlpatterns = [
    path("hello/", views.Hello.as_view()),
    path("checkrunner/", views.CheckRunner.as_view()),
    path("<str:agentid>/checkrunner/", views.CheckRunner.as_view()),
    path("<int:pk>/<str:agentid>/taskrunner/", views.TaskRunner.as_view()),
    path("saltminion/", views.SaltMinion.as_view()),
    path("<str:agentid>/saltminion/", views.SaltMinion.as_view()),
    path("<int:pk>/meshinfo/", views.MeshInfo.as_view()),
    path("meshexe/", views.MeshExe.as_view()),
    path("sysinfo/", views.SysInfo.as_view()),
    path("newagent/", views.NewAgent.as_view()),
    path("winupdater/", views.WinUpdater.as_view()),
    path("<str:agentid>/winupdater/", views.WinUpdater.as_view()),
]
