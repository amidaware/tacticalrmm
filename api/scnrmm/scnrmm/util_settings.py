# this file must not import anything from django settings to avoid circular import issues

from urllib.parse import urlparse

import tldextract


def get_webdomain(url: str) -> str:
    return urlparse(url).netloc


def get_root_domain(subdomain) -> str:
    no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=())
    extracted = no_fetch_extract(subdomain)
    return f"{extracted.domain}.{extracted.suffix}"


def get_backend_url(subdomain, proto, port) -> str:
    url = f"{proto}://{subdomain}"
    if port:
        url = f"{url}:{port}"

    return url
