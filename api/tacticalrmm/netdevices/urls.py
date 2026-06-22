from django.urls import path

from . import views

urlpatterns = [
    path("", views.GetAddNetworkDevices.as_view()),
    path("<int:pk>/", views.GetUpdateDeleteNetworkDevice.as_view()),
    path("<int:pk>/connect/", views.NetworkDeviceConnect.as_view()),
]
