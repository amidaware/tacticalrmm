import json

from django.conf import settings
from django.http import HttpResponse


def monitoring_view(function):
    def wrap(request, *args, **kwargs):
        if request.method != "POST":
            return HttpResponse("Invalid request type\n", status=400)

        try:
            data = json.loads(request.body)
        except:
            return HttpResponse("Invalid json\n", status=400)

        if "auth" not in data.keys():
            return HttpResponse("Invalid payload\n", status=400)

        token = getattr(settings, "MON_TOKEN", "")
        if not token:
            return HttpResponse("Missing token\n", status=401)

        if data.get("auth") != token:
            return HttpResponse("Not authenticated\n", status=401)

        return function(request, *args, **kwargs)

    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap
