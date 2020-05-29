from django.urls import path
from . import views, scriptviews

urlpatterns = [
    path("checks/", views.GetAddCheck.as_view()),
    path("<pk>/loadchecks/", views.load_checks),
    path("<pk>/loadpolicychecks/", views.load_policy_checks),
    path("checkrunner/", views.check_runner),
    path("getstandardcheck/<checktype>/<pk>/", views.get_standard_check),
    path("editstandardcheck/", views.edit_standard_check),
    path("deletestandardcheck/", views.delete_standard_check),
    path("getdisks/<pk>/", views.get_disks),
    path("getalldisks/", views.get_disks_for_policies),
    path("checkalert/", views.check_alert),
    path("getscripts/", views.get_scripts),
    path("uploadscript/", scriptviews.UploadScript.as_view()),
    path("editscript/", scriptviews.EditScript.as_view()),
    path("viewscriptcode/<pk>/", scriptviews.view_script_code),
    path("deletescript/", scriptviews.delete_script),
    path("getscript/<pk>/", scriptviews.get_script),
    path("downloadscript/<pk>/", scriptviews.download_script),
    path("runchecks/<pk>/", views.run_checks),
    path("checkresults/", views.check_results),
]
