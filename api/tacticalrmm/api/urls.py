from django.urls import path
from . import views

urlpatterns = [
    path("hello/", views.hello),
    path("update/", views.update),
    path("add/", views.add),
    path("token/", views.create_auth_token),
    path("acceptsaltkey/", views.accept_salt_key),
    path("triggerpatchscan/", views.trigger_patch_scan),
    path("firstinstall/", views.on_agent_first_install),
    path("<int:pk>/checkrunner/", views.CheckRunner.as_view()),
    path("<int:pk>/taskrunner/", views.TaskRunner.as_view()),
    path("<int:pk>/saltinfo/", views.SaltInfo.as_view()),
    path("<int:pk>/meshinfo/", views.MeshInfo.as_view()),
]
