from django.urls import path
from . import views

urlpatterns = [
    path("<pk>/services/", views.get_services),
    path("<pk>/refreshedservices/", views.get_refreshed_services),
    path("serviceaction/", views.service_action),
    path("<pk>/<svcname>/servicedetail/", views.service_detail),
    path("editservice/", views.edit_service),
]