import collections
import time

from django.conf import settings


class _RateLimiter:
    def __init__(self, max_attempts: int = 10, window: int = 60):
        self._max_attempts = max_attempts
        self._window = window
        self._attempts: dict[str, list[float]] = collections.defaultdict(list)

    def allow(self, ip: str) -> bool:
        now = time.time()
        cutoff = now - self._window
        attempts = self._attempts[ip]
        attempts[:] = [t for t in attempts if t > cutoff]
        if len(attempts) >= self._max_attempts:
            return False
        attempts.append(now)
        return True

    def reset(self, ip: str) -> None:
        self._attempts.pop(ip, None)


def _make_rate_limiter():
    return _RateLimiter(
        max_attempts=getattr(settings, "SSH_RATE_LIMIT_ATTEMPTS", 10),
        window=getattr(settings, "SSH_RATE_LIMIT_WINDOW", 60),
    )


_rate_limiter = _make_rate_limiter()
