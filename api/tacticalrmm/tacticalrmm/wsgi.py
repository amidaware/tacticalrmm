"""
WSGI config for tacticalrmm project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tacticalrmm.settings")

application = get_wsgi_application()

# Load the URL configuration and all views once, in the uWSGI master,
# so forked workers inherit them instead of importing on their first request.
from django.urls import get_resolver  # noqa: E402

get_resolver().url_patterns
