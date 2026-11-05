from django.urls import path

from . import views

urlpatterns = [
    path("", views.GetEditBranding.as_view()),
    path("image/<str:kind>/", views.BrandingImage.as_view()),
]
