from django.urls import path
from . import views

urlpatterns = [
    path("checkrunner/", views.CheckRunner.as_view()),
    path("<str:agentid>/checkrunner/", views.CheckRunner.as_view()),
    path("<str:agentid>/checkinterval/", views.CheckRunnerInterval.as_view()),
    path("<int:pk>/<str:agentid>/taskrunner/", views.TaskRunner.as_view()),
    path("meshexe/", views.MeshExe.as_view()),
    path("sysinfo/", views.SysInfo.as_view()),
    path("newagent/", views.NewAgent.as_view()),
    path("software/", views.Software.as_view()),
    path("installer/", views.Installer.as_view()),
]
