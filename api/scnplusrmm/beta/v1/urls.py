from rest_framework import routers
from .agent import views as agent
from .client import views as client
from .site import views as site

router = routers.DefaultRouter()

router.register("agent", agent.AgentViewSet, basename="agent")
router.register("client", client.ClientViewSet, basename="client")
router.register("site", site.SiteViewSet, basename="site")

urlpatterns = router.urls
