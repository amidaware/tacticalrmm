import re
from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError

LAYOUT_KEYS = ("order", "hidden")
MAX_ITEMS = 100
_ITEM_ID = re.compile(r"^[a-z0-9_]{1,50}$")


def validate_agent_menu_layout(value: Any) -> None:
    """Shape check only: the menu item ids are owned by the frontend registry."""
    if not isinstance(value, dict):
        raise ValidationError("The agent menu layout must be an object.")

    unknown = set(value) - set(LAYOUT_KEYS)
    if unknown:
        raise ValidationError(
            f"Unknown agent menu layout keys: {', '.join(sorted(unknown))}."
        )

    for key in LAYOUT_KEYS:
        items = value.get(key, [])
        if not isinstance(items, list):
            raise ValidationError(f"'{key}' must be a list.")
        if len(items) > MAX_ITEMS:
            raise ValidationError(f"'{key}' may contain at most {MAX_ITEMS} entries.")
        if not all(isinstance(i, str) and _ITEM_ID.match(i) for i in items):
            raise ValidationError(f"'{key}' contains an invalid menu item id.")
        if len(set(items)) != len(items):
            raise ValidationError(f"'{key}' contains duplicate menu item ids.")


def effective_agent_menu_layout(
    user_layout: Optional[Dict[str, Any]],
    company_layout: Optional[Dict[str, Any]],
    allow_user: bool,
) -> Dict[str, Any]:
    # a locked company layout wins, but the user's own layout stays stored
    if allow_user and user_layout:
        return user_layout
    return company_layout or {}
