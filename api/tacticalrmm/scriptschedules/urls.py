from django.urls import path

from . import views

urlpatterns = [
    # CRUD
    path("", views.openframe_script_schedule_list_create),
    path("<int:pk>/", views.openframe_script_schedule_detail),
    # Agent management
    path("<int:pk>/agents/", views.openframe_script_schedule_agents),
    # Execution history
    path("<int:pk>/history/", views.openframe_script_schedule_history),
]
