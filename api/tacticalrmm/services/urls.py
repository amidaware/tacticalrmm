from django.urls import path

from . import views

urlpatterns = [
    path("<agent:agent_id>/", views.GetServices.as_view()),
    path("<agent:agent_id>/<str:svcname>/", views.GetEditActionService.as_view()),
]
