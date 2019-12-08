from django.urls import path
from . import views

urlpatterns = [
    path("hello/", views.hello),
    path("update/", views.update),
    path("add/", views.add),
    path("agentauth/", views.agent_auth),
    path("getmeshnodes/", views.get_mesh_nodes),
    path("token/", views.create_auth_token),
    path("acceptsaltkey/<hostname>/", views.accept_salt_key),
    path("deleteagent/", views.delete_agent),
    path("getrmmlog/<mode>/<hostname>/<order>/", views.get_log),
    path("downloadrmmlog/", views.download_log),
    path("getmeshexe/", views.get_mesh_exe),
    path("uploadmeshagent/", views.UploadMeshAgent.as_view()),
    path("triggerpatchscan/", views.trigger_patch_scan),
]