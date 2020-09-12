from django.urls import path
from . import views

urlpatterns = [
    path("newagent/", views.NewAgent.as_view()),
    path("meshexe/", views.MeshExe.as_view()),
    path("saltminion/", views.SaltMinion.as_view()),
    path("<str:agentid>/saltminion/", views.SaltMinion.as_view()),
    path("sysinfo/", views.SysInfo.as_view()),
]
