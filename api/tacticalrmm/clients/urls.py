from django.urls import path
from . import views

urlpatterns = [
    path("clients/", views.GetAddClients.as_view()),
    path("<int:pk>/client/", views.GetUpdateDeleteClient.as_view()),
    path("sites/", views.GetAddSites.as_view()),
    path("listclients/", views.list_clients),
    path("listsites/", views.list_sites),
    path("editclient/", views.edit_client),
    path("addsite/", views.add_site),
    path("editsite/", views.edit_site),
    path("loadtree/", views.load_tree),
    path("loadclients/", views.load_clients),
]
