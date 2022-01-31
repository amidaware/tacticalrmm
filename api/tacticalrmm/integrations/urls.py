from django.urls import path

from . import views

urlpatterns = [
    path("", views.GetIntegrations.as_view()),
    path("<int:pk>/", views.GetIntegration.as_view()),
    path("<int:pk>/associate_client/", views.GetAssociateIntegration.as_view())
]
