from django.urls import path
from django.conf import settings

from . import views

urlpatterns = [
    path("settings/", views.GetEditCoreSettings.as_view()),
    path("version/", views.version),
    path("emailtest/", views.email_test),
    path("dashinfo/", views.dashboard_info),
    path("servermaintenance/", views.server_maintenance),
    path("customfields/", views.GetAddCustomFields.as_view()),
    path("customfields/<int:pk>/", views.GetUpdateDeleteCustomFields.as_view()),
    path("codesign/", views.CodeSign.as_view()),
    path("keystore/", views.GetAddKeyStore.as_view()),
    path("keystore/<int:pk>/", views.UpdateDeleteKeyStore.as_view()),
    path("urlaction/", views.GetAddURLAction.as_view()),
    path("urlaction/<int:pk>/", views.UpdateDeleteURLAction.as_view()),
    path("schedules/", views.GetAddSchedule.as_view()),
    path("schedules/<int:pk>/", views.UpdateDeleteSchedule.as_view()),
    path("urlaction/run/", views.RunURLAction.as_view()),
    path("urlaction/run/test/", views.RunTestURLAction.as_view()),
    path("smstest/", views.TwilioSMSTest.as_view()),
    path("clearcache/", views.clear_cache),
    path("openai/generate/", views.OpenAICodeCompletion.as_view()),
    # Pi.dev AI providers & models
    path("ai/providers/", views.GetAddAIProvider.as_view()),
    path("ai/providers/<int:pk>/", views.UpdateDeleteAIProvider.as_view()),
    path("ai/available-models/", views.AIAvailableModels.as_view()),
    path("ai/models/", views.GetAddAIModel.as_view()),
    path("ai/models/<int:pk>/", views.UpdateDeleteAIModel.as_view()),
    path("ai/tasks/", views.GetAddAITask.as_view()),
    path("ai/tasks/<int:pk>/", views.UpdateDeleteAITask.as_view()),
    path("ai/tasks/<int:pk>/run/", views.RunAITaskNow.as_view()),
    path("ai/email/", views.AISendEmail.as_view()),
    path("ai/runs/", views.AITaskRuns.as_view()),
    path("ai/runs/<str:run_id>/live/", views.AITaskRunLive.as_view()),
    path("ai/bulk/", views.GetAddBulkAICommand.as_view()),
    path("ai/bulk/<int:pk>/", views.UpdateDeleteBulkAICommand.as_view()),
    path("ai/bulk/<int:pk>/run/", views.RunBulkAICommandNow.as_view()),
    path("ai/bulk/<int:pk>/results/", views.BulkAICommandResults.as_view()),
    path("ai/bulk/<int:pk>/stop/", views.StopBulkAICommand.as_view()),
    path("ai/stop-all/", views.StopAllAIRuns.as_view()),
    path("ai/bulk/preview/", views.PreviewBulkAITargets.as_view()),
    path("webtermperms/", views.webterm_perms),
]

if not getattr(settings, "DEMO", False):
    urlpatterns += (
        path("status/", views.status),  # TODO deprecated
        path("v2/status/", views.status_v2),
    )


if not (
    getattr(settings, "HOSTED", False)
    or getattr(settings, "TRMM_DISABLE_SERVER_SCRIPTS", False)
    or getattr(settings, "DEMO", False)
):
    urlpatterns += (path("serverscript/test/", views.TestRunServerScript.as_view()),)
