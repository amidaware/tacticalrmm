from django.urls import path
from . import views

urlpatterns = [
    path("getcoresettings/", views.get_core_settings),
    path("editsettings/", views.edit_settings),
]
