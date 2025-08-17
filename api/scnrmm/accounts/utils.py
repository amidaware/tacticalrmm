from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django.http import HttpRequest

    from accounts.models import User


def is_root_user(*, request: "HttpRequest", user: "User") -> bool:
    root = (
        hasattr(settings, "ROOT_USER")
        and request.user != user
        and user.username == settings.ROOT_USER
    )
    demo = (
        getattr(settings, "DEMO", False) and request.user.username == settings.ROOT_USER
    )
    return root or demo


def is_superuser(user: "User") -> bool:
    return user.role and getattr(user.role, "is_superuser")
