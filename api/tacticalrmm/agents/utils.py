import random
import urllib.parse

import requests
from django.conf import settings


def get_exegen_url() -> str:
    urls: list[str] = settings.EXE_GEN_URLS
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
        except:
            continue

        if r.status_code == 200:
            return url

    return random.choice(urls)


def get_winagent_url(arch: str) -> str:
    from core.models import CodeSignToken

    try:
        codetoken = CodeSignToken.objects.first().token
        base_url = get_exegen_url() + "/api/v1/winagents/?"
        params = {
            "version": settings.LATEST_AGENT_VER,
            "arch": arch,
            "token": codetoken,
        }
        dl_url = base_url + urllib.parse.urlencode(params)
    except:
        dl_url = settings.DL_64 if arch == "64" else settings.DL_32

    return dl_url
