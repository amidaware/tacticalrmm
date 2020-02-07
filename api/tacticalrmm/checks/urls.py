from django.urls import path
from . import views, scriptviews

urlpatterns = [
    path("<pk>/loadchecks/", views.load_checks),
    path("checkrunner/", views.check_runner),
    path("getstandardcheck/<checktype>/<pk>/", views.get_standard_check),
    path("addstandardcheck/", views.add_standard_check),
    path("editstandardcheck/", views.edit_standard_check),
    path("deletestandardcheck/", views.delete_standard_check),
    path("getdisks/<pk>/", views.get_disks),
    path("checkalert/", views.check_alert),
    path("updatepingcheck/", views.update_ping_check),
    path("updatescriptcheck/", views.update_script_check),
    path("getscripts/", views.get_scripts),
    path("uploadscript/", scriptviews.UploadScript.as_view()),
    path("editscript/", scriptviews.EditScript.as_view()),
    path("viewscriptcode/<pk>/", scriptviews.view_script_code),
    path("deletescript/", scriptviews.delete_script),
    path("getscript/<pk>/", scriptviews.get_script),
    path("downloadscript/<pk>/", scriptviews.download_script),
]
