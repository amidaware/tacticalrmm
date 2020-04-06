from django.urls import path
from . import views

urlpatterns = [
    path("policies/", views.GetAddPolicies.as_view()),
    path("policies/<pk>/", views.GetAddDeletePolicy.as_view()),
]
