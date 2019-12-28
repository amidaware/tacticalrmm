from django.urls import path
from . import views

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
]
