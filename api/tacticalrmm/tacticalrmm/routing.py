from tacticalrmm.utils import KnoxAuthMiddlewareStack

from channels.routing import ProtocolTypeRouter, URLRouter
from .urls import ws_urlpatterns

application = ProtocolTypeRouter(
    {"websocket": KnoxAuthMiddlewareStack(URLRouter(ws_urlpatterns))}
)