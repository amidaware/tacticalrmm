from typing import TYPE_CHECKING

from django.conf import settings

from core.utils import get_core_settings

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


def can_dashboard_login(user: "User") -> bool:
    if user.block_dashboard_login or user.is_sso_user:
        return False

    core_settings = get_core_settings()
    if not user.is_superuser and core_settings.block_local_user_logon:
        return False

    return True
