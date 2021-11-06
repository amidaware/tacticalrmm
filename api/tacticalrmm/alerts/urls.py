from django.urls import path

from . import views

urlpatterns = [
    path("", views.GetAddAlerts.as_view()),
    path("<int:pk>/", views.GetUpdateDeleteAlert.as_view()),
    path("bulk/", views.BulkAlerts.as_view()),
    path("templates/", views.GetAddAlertTemplates.as_view()),
    path("templates/<int:pk>/", views.GetUpdateDeleteAlertTemplate.as_view()),
    path("templates/<int:pk>/related/", views.RelatedAlertTemplate.as_view()),
]
