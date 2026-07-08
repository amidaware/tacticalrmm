"""
Pi.dev AI assistant - short-lived session token store.

Mirrors the Remote Web Proxy pattern (agents/web_proxy.py) but writes the session
blob to redis as raw JSON (not Django's pickled cache) so the Node.js
`pi-trmm-bridge` service can read it directly with ioredis.

Key: pi_session:<token>  ->  JSON {agent_id, username, provider, model, ...}
"""

import json
import secrets
from typing import Any, Optional

from django.conf import settings
from redis import from_url

SESSION_PREFIX = "pi_session:"
SESSION_TTL = 60 * 60 * 8  # 8 hours


def _redis():
    return from_url(f"redis://{settings.REDIS_HOST}:6379", decode_responses=True)


def create_pi_session(*, data: dict[str, Any]) -> str:
    token = secrets.token_urlsafe(32)
    with _redis() as conn:
        conn.set(f"{SESSION_PREFIX}{token}", json.dumps(data), ex=SESSION_TTL)
    return token


def get_pi_session(token: str) -> Optional[dict[str, Any]]:
    with _redis() as conn:
        raw = conn.get(f"{SESSION_PREFIX}{token}")
    if not raw:
        return None
    return json.loads(raw)


def delete_pi_session(token: str) -> None:
    with _redis() as conn:
        conn.delete(f"{SESSION_PREFIX}{token}")
