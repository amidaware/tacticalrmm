import re
from typing import Optional

PNG = "image/png"
JPEG = "image/jpeg"
WEBP = "image/webp"
SVG = "image/svg+xml"
ICO = "image/x-icon"

ALLOWED_TYPES = {
    "logo": (PNG, JPEG, WEBP, SVG),
    "favicon": (ICO, PNG, SVG),
    "login_background": (PNG, JPEG, WEBP),
}

MAX_SIZE = {
    "logo": 512 * 1024,
    "favicon": 512 * 1024,
    "login_background": 2 * 1024 * 1024,
}

# whitespace, xml declaration, comments and doctype may precede the <svg> root
_SVG_START = re.compile(
    rb"^(?:\s+|<\?xml[^>]*\?>|<!--.*?-->|<!DOCTYPE[^>]*>)*<svg[\s>]",
    re.DOTALL | re.IGNORECASE,
)


def detect_image_type(data: bytes) -> Optional[str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if data.startswith(b"\xff\xd8\xff"):
        return JPEG
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return WEBP
    if data.startswith(b"\x00\x00\x01\x00"):
        return ICO
    if _SVG_START.match(data[:4096].removeprefix(b"\xef\xbb\xbf")):
        return SVG
    return None


def validate_image(kind: str, data: bytes) -> str:
    """Returns the detected MIME type or raises ValueError with a user facing message."""
    if not data:
        raise ValueError("The file is empty.")

    if len(data) > MAX_SIZE[kind]:
        raise ValueError(f"The file is larger than {MAX_SIZE[kind] // 1024} KB.")

    mime = detect_image_type(data)
    if mime not in ALLOWED_TYPES[kind]:
        raise ValueError("This file type is not allowed here.")

    return mime
