from django.urls import path, include
from . import views

urlpatterns = [ 
    path('organizations/', views.GetOrganizations.as_view()),
    path('organizations/<str:organization_id>/', views.GetOrganization.as_view()),
    path('<str:pk>/networks/', views.GetNetworks.as_view()),
    path('<str:pk>/devices/statuses/', views.GetDevices.as_view()),
    path('<str:pk>/overview/<str:timespan>/', views.GetOverview.as_view()),
    path('<str:pk>/networks/uplinks/', views.GetNetworkUplinks.as_view()),
    path('<str:pk>/top_clients/<str:timespan>/', views.GetTopClients.as_view()),
    path('<str:pk>/client/<str:mac>/', views.GetClient.as_view()),
    path('<str:network_id>/applications/traffic/<str:timespan>/', views.GetNetworkApplicationTraffic.as_view()),
    path('<str:network_id>/clients/traffic/<str:timespan>/', views.GetNetworkClientTraffic.as_view()),
    path('<str:network_id>/clients/<str:client_mac>/policy/', views.GetClientPolicy.as_view()),
    path('<str:network_id>/events/<str:timespan>/', views.GetNetworkEvents.as_view())
]