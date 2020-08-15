from django.urls import path
from . import views

urlpatterns = [
    path("alerts/", views.GetAddAlerts.as_view()),
    path("alerts/<int:pk>/", views.GetUpdateDeleteAlert.as_view()),
]
