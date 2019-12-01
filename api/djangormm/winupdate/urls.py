from django.urls import path
from . import views

urlpatterns = [
    path("<pk>/getwinupdates/", views.get_win_updates),
]