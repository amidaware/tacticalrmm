import os
import django

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tacticalrmm.settings")
django.setup()

from tacticalrmm.utils import KnoxAuthMiddlewareStack
from .urls import ws_urlpatterns


application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": KnoxAuthMiddlewareStack(URLRouter(ws_urlpatterns)),
    }
)
