from django.urls import path

from . import views

urlpatterns = [
    path("clients/", views.GetAddClients.as_view()),
    path("<int:pk>/client/", views.GetUpdateClient.as_view()),
    path("<int:pk>/<int:sitepk>/", views.DeleteClient.as_view()),
    path("tree/", views.GetClientTree.as_view()),
    path("sites/", views.GetAddSites.as_view()),
    path("sites/<int:pk>/", views.GetUpdateSite.as_view()),
    path("sites/<int:pk>/<int:sitepk>/", views.DeleteSite.as_view()),
    path("deployments/", views.AgentDeployment.as_view()),
    path("<int:pk>/deployment/", views.AgentDeployment.as_view()),
    path("<str:uid>/deploy/", views.GenerateAgent.as_view()),
]
