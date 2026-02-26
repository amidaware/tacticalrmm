from django.urls import path
from rest_framework import routers

from .scripts import views as scripts

router = routers.DefaultRouter()

router.register("scripts", scripts.ScriptViewSet, basename="scripts")

urlpatterns = router.urls + [
    path("scripts/filters/", scripts.ScriptFiltersView.as_view()),
]
