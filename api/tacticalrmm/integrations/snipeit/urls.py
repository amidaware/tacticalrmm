from django.urls import path, include
from . import views


urlpatterns = [ 
    path('hardware/', views.GetHardware.as_view()),
    path('hardware/<str:asset_id>/', views.GetAsset.as_view()),
    path('hardware/by_tag/<str:asset_tag>/', views.GetAssetByTag.as_view()),
    path('hardware/<str:asset_id>/checkout/', views.GetAssetCheckout.as_view()),
    path('hardware/<str:asset_id>/checkin/', views.GetAssetCheckin.as_view()),
    path('companies/', views.GetCompanies.as_view()),
    path('companies/<str:company_id>/', views.GetCompany.as_view()),
    path('statuslabels/', views.GetStatusLabels.as_view()),
    path('models/', views.GetModels.as_view()),
    path('manufacturers/', views.GetManufacturers.as_view()),
    path('categories/', views.GetCategories.as_view()),
    path('locations/', views.GetLocations.as_view()),
    path('locations/<str:location_id>/', views.GetLocation.as_view()),
    path('users/', views.GetUsers.as_view()),
    path('users/<str:user_id>/', views.GetUser.as_view()),
]