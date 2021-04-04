from django.urls import path

from . import views

urlpatterns = [
    path("listagents/", views.AgentsTableList.as_view()),
    path("listagentsnodetail/", views.list_agents_no_detail),
    path("<int:pk>/agenteditdetails/", views.agent_edit_details),
    path("overdueaction/", views.overdue_action),
    path("sendrawcmd/", views.send_raw_cmd),
    path("<pk>/agentdetail/", views.agent_detail),
    path("<int:pk>/meshcentral/", views.meshcentral),
    path("<str:arch>/getmeshexe/", views.get_mesh_exe),
    path("uninstall/", views.uninstall),
    path("editagent/", views.edit_agent),
    path("<pk>/geteventlog/<logtype>/<days>/", views.get_event_log),
    path("getagentversions/", views.get_agent_versions),
    path("updateagents/", views.update_agents),
    path("<pk>/getprocs/", views.get_processes),
    path("<pk>/<pid>/killproc/", views.kill_proc),
    path("reboot/", views.Reboot.as_view()),
    path("installagent/", views.install_agent),
    path("<int:pk>/ping/", views.ping),
    path("recover/", views.recover),
    path("runscript/", views.run_script),
    path("<int:pk>/recovermesh/", views.recover_mesh),
    path("<int:pk>/notes/", views.GetAddNotes.as_view()),
    path("<int:pk>/note/", views.GetEditDeleteNote.as_view()),
    path("bulk/", views.bulk),
    path("maintenance/", views.agent_maintenance),
    path("<int:pk>/wmi/", views.WMI.as_view()),
]
