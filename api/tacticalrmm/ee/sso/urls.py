    
from django.urls import path
from django.urls import include

from . import views

urlpatterns = [
    path("", include("allauth.urls")),
    path("ssoproviders/", views.GetAddSSOProvider.as_view()),
    path("ssoproviders/<int:pk>/", views.GetUpdateDeleteSSOProvider.as_view()),
]