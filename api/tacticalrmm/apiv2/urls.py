from django.urls import path
from . import views
from apiv3 import views as v3_views

urlpatterns = [
    path("newagent/", v3_views.NewAgent.as_view()),
    path("meshexe/", v3_views.MeshExe.as_view()),
    path("saltminion/", v3_views.SaltMinion.as_view()),
    path("<str:agentid>/saltminion/", v3_views.SaltMinion.as_view()),
    path("sysinfo/", v3_views.SysInfo.as_view()),
    path("hello/", v3_views.Hello.as_view()),
    path("checkrunner/", views.CheckRunner.as_view()),
    path("<str:agentid>/checkrunner/", views.CheckRunner.as_view()),
]
