from django.urls import path

from . import file_transfer_views, views

urlpatterns = [
    path(
        "file-transfers/<uuid:session_id>/next-chunk/",
        file_transfer_views.FileTransferNextChunk.as_view(),
        name="file_transfer_next_chunk",
    ),
    path(
        "file-transfers/<uuid:session_id>/ack/",
        file_transfer_views.FileTransferAck.as_view(),
        name="file_transfer_ack",
    ),
    path(
        "file-transfers/<uuid:session_id>/download-chunk/",
        file_transfer_views.FileTransferDownloadPutChunk.as_view(),
        name="file_transfer_download_put_chunk",
    ),
    path(
        "file-transfers/<uuid:session_id>/fail/",
        file_transfer_views.FileTransferFail.as_view(),
        name="file_transfer_fail",
    ),
    path(
        "file-transfers/<uuid:session_id>/archive-ready/",
        file_transfer_views.FileTransferArchiveReady.as_view(),
        name="file_transfer_archive_ready",
    ),
    path(
        "file-transfers/<uuid:session_id>/extract-progress/",
        file_transfer_views.FileTransferExtractProgress.as_view(),
        name="file_transfer_extract_progress",
    ),
    path(
        "file-transfers/<uuid:session_id>/extract-done/",
        file_transfer_views.FileTransferExtractDone.as_view(),
        name="file_transfer_extract_done",
    ),
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
    path("<int:pk>/<str:agentid>/histresult/", views.AgentHistoryResult.as_view()),
    path("<str:agentid>/config/", views.AgentConfig.as_view()),
    path("<str:agentid>/meshreinstall/", views.MeshReinstall.as_view()),
]
