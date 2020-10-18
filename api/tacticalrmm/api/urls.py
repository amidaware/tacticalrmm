from django.urls import path
from . import views
from apiv3 import views as v3_views

urlpatterns = [
    path("triggerpatchscan/", views.trigger_patch_scan),
    path("<int:pk>/checkrunner/", views.CheckRunner.as_view()),
    path("<int:pk>/taskrunner/", views.TaskRunner.as_view()),
    path("<int:pk>/saltinfo/", views.SaltInfo.as_view()),
    path("<int:pk>/meshinfo/", v3_views.MeshInfo.as_view()),
]
