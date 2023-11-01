"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

from django.urls import path

from . import views

urlpatterns = [
    # report templates
    path("templates/", views.GetAddReportTemplate.as_view()),
    path("templates/<int:pk>/", views.GetEditDeleteReportTemplate.as_view()),
    path("templates/<int:pk>/run/", views.GenerateReport.as_view()),
    path("templates/<int:pk>/export/", views.ExportReportTemplate.as_view()),
    path("templates/preview/", views.GenerateReportPreview.as_view()),
    path("templates/preview/analysis/", views.GetAllowedValues.as_view()),
    path("templates/import/", views.ImportReportTemplate.as_view()),
    # shared templates
    path("templates/shared/", views.SharedTemplatesRepo.as_view()),
    # report assets
    path("assets/", views.GetReportAssets.as_view()),
    path("assets/all/", views.GetAllAssets.as_view()),
    path("assets/rename/", views.RenameReportAsset.as_view()),
    path("assets/newfolder/", views.CreateAssetFolder.as_view()),
    path("assets/delete/", views.DeleteAssets.as_view()),
    path("assets/upload/", views.UploadAssets.as_view()),
    path("assets/download/", views.DownloadAssets.as_view()),
    # report html templates
    path("htmltemplates/", views.GetAddReportHTMLTemplate.as_view()),
    path("htmltemplates/<int:pk>/", views.GetEditDeleteReportHTMLTemplate.as_view()),
    # report data queries
    path("dataqueries/", views.GetAddReportDataQuery.as_view()),
    path("dataqueries/<int:pk>/", views.GetEditDeleteReportDataQuery.as_view()),
    # serving assets
    path("assets/<path:path>", views.NginxRedirect.as_view()),
    path("queryschema/", views.QuerySchema.as_view()),
]
