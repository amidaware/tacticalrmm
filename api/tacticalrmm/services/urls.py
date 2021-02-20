from django.urls import path

from . import views

urlpatterns = [
    path("<int:pk>/services/", views.get_services),
    path("defaultservices/", views.default_services),
    path("serviceaction/", views.service_action),
    path("<int:pk>/<svcname>/servicedetail/", views.service_detail),
    path("editservice/", views.edit_service),
]
