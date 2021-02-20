from django.urls import path

from . import views

urlpatterns = [
    path("alerts/", views.GetAddAlerts.as_view()),
    path("bulk/", views.BulkAlerts.as_view()),
    path("alerts/<int:pk>/", views.GetUpdateDeleteAlert.as_view()),
    path("alerttemplates/", views.GetAddAlertTemplates.as_view()),
    path("alerttemplates/<int:pk>/", views.GetUpdateDeleteAlertTemplate.as_view()),
    path("alerttemplates/<int:pk>/related/", views.RelatedAlertTemplate.as_view()),
]
