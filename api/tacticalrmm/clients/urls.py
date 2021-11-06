from django.urls import path

from . import views

urlpatterns = [
    path("", views.GetAddClients.as_view()),
    path("<int:pk>/", views.GetUpdateDeleteClient.as_view()),
    path("sites/", views.GetAddSites.as_view()),
    path("sites/<int:pk>/", views.GetUpdateDeleteSite.as_view()),
    path("deployments/", views.AgentDeployment.as_view()),
    path("deployments/<int:pk>/", views.AgentDeployment.as_view()),
    path("<str:uid>/deploy/", views.GenerateAgent.as_view()),
]
