from django.urls import path

from autotasks.views import GetAddAutoTasks
from checks.views import GetAddChecks
from logs.views import PendingActions

from . import views

urlpatterns = [
    # agent views
    path("", views.GetAgents.as_view()),
    path("<agent:agent_id>/", views.GetUpdateDeleteAgent.as_view()),
    path("<agent:agent_id>/cmd/", views.send_raw_cmd),
    path("<agent:agent_id>/runscript/", views.run_script),
    path("<agent:agent_id>/wmi/", views.WMI.as_view()),
    path("<agent:agent_id>/recover/", views.recover),
    path("<agent:agent_id>/reboot/", views.Reboot.as_view()),
    path("<agent:agent_id>/shutdown/", views.Shutdown.as_view()),
    path("<agent:agent_id>/ping/", views.ping),
    # alias for checks get view
    path("<agent:agent_id>/checks/", GetAddChecks.as_view()),
    # alias for autotasks get view
    path("<agent:agent_id>/tasks/", GetAddAutoTasks.as_view()),
    # alias for pending actions get view
    path("<agent:agent_id>/pendingactions/", PendingActions.as_view()),
    # agent remote background
    path("<agent:agent_id>/meshcentral/", views.AgentMeshCentral.as_view()),
    path("<agent:agent_id>/meshcentral/recover/", views.AgentMeshCentral.as_view()),
    path("<agent:agent_id>/processes/", views.AgentProcesses.as_view()),
    path("<agent:agent_id>/processes/<int:pid>/", views.AgentProcesses.as_view()),
    path("<agent:agent_id>/eventlog/<str:logtype>/<int:days>/", views.get_event_log),
    # agent history
    path("history/", views.AgentHistoryView.as_view()),
    path("<agent:agent_id>/history/", views.AgentHistoryView.as_view()),
    # agent notes
    path("notes/", views.GetAddNotes.as_view()),
    path("notes/<int:pk>/", views.GetEditDeleteNote.as_view()),
    path("<agent:agent_id>/notes/", views.GetAddNotes.as_view()),
    # bulk actions
    path("maintenance/bulk/", views.agent_maintenance),
    path("actions/bulk/", views.bulk),
    path("versions/", views.get_agent_versions),
    path("update/", views.update_agents),
    path("installer/", views.install_agent),
    path("bulkrecovery/", views.bulk_agent_recovery),
    path("scripthistory/", views.ScriptRunHistory.as_view()),
    path("<agent:agent_id>/wol/", views.wol),
]
