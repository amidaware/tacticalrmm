import os

from channels.routing import ProtocolTypeRouter, URLRouter  # isort:skip
from django.core.asgi import get_asgi_application  # isort:skip

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tacticalrmm.settings")  # isort:skip
django_asgi_app = get_asgi_application()  # isort:skip

from tacticalrmm.utils import KnoxAuthMiddlewareStack  # isort:skip # noqa
from .urls import ws_urlpatterns  # isort:skip # noqa


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": KnoxAuthMiddlewareStack(URLRouter(ws_urlpatterns)),
    }
)
