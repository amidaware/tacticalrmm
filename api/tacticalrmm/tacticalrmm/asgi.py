import os

import django

from channels.routing import ProtocolTypeRouter, URLRouter  # isort:skip
from django.core.asgi import get_asgi_application  # isort:skip

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tacticalrmm.settings")
django.setup()

from tacticalrmm.utils import KnoxAuthMiddlewareStack  # isort:skip
from .urls import ws_urlpatterns  # isort:skip


application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": KnoxAuthMiddlewareStack(URLRouter(ws_urlpatterns)),
    }
)
