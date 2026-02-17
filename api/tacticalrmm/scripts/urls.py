from django.urls import path

from scriptschedules.views import openframe_schedules_for_script

from . import views

urlpatterns = [
    path("", views.GetAddScripts.as_view()),
    path("<int:pk>/", views.GetUpdateDeleteScript.as_view()),
    path("snippets/", views.GetAddScriptSnippets.as_view()),
    path("snippets/<int:pk>/", views.GetUpdateDeleteScriptSnippet.as_view()),
    path("<agent:agent_id>/test/", views.TestScript.as_view()),
    path("<int:pk>/download/", views.download),
    # Openframe: which schedules reference this script
    path("<int:script_pk>/schedules/", openframe_schedules_for_script),
]
