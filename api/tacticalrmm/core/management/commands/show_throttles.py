import time

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

PERIODS = {
    "second": 1,
    "sec": 1,
    "s": 1,
    "minute": 60,
    "min": 60,
    "m": 60,
    "hour": 60 * 60,
    "hr": 60 * 60,
    "h": 60 * 60,
    "day": 60 * 60 * 24,
    "d": 60 * 60 * 24,
}


def parse_rate(rate):
    count, period = rate.split("/")
    return int(count), PERIODS[period]


def human_seconds(seconds):
    seconds = max(0, int(seconds))

    if seconds < 60:
        return f"{seconds}s"

    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"

    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes}m"

    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h"


class Command(BaseCommand):
    help = "Show current throttle status"

    def handle(self, *args, **options):
        version = 1
        now = time.time()

        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})

        keys = list(cache.iter_keys_pattern("throttle_*", version=version))  # type: ignore

        if not keys:
            self.stdout.write("No active login throttles found.")
            return

        rows = []

        for key in sorted(keys):
            raw_key = key.decode() if isinstance(key, bytes) else key
            clean_key = raw_key.removeprefix(f":{version}:")

            matched_scope = None
            ident = None

            for scope in rates:
                prefix = f"throttle_{scope}_"
                if clean_key.startswith(prefix):
                    matched_scope = scope
                    ident = clean_key.removeprefix(prefix)
                    break

            if not matched_scope:
                continue

            limit, duration = parse_rate(rates[matched_scope])

            history = cache.get(clean_key) or []

            active_attempts = [ts for ts in history if ts > now - duration]

            attempts = len(active_attempts)
            remaining = max(0, limit - attempts)
            throttled = attempts >= limit

            if throttled and active_attempts:
                oldest_attempt = min(active_attempts)
                retry_after = duration - (now - oldest_attempt)
            else:
                retry_after = 0

            rows.append(
                {
                    "scope": matched_scope,
                    "client": ident,
                    "attempts": attempts,
                    "limit": limit,
                    "window": rates[matched_scope].split("/")[1],
                    "remaining": remaining,
                    "status": "THROTTLED" if throttled else "OK",
                    "retry_after": human_seconds(retry_after) if throttled else "-",
                }
            )

        if not rows:
            self.stdout.write("No active throttle entries found.")
            return

        self.stdout.write(
            f"{'Status':<12} {'Throttle':<18} {'Client':<18} "
            f"{'Attempts':<12} {'Remaining':<10} {'Retry After'}"
        )
        self.stdout.write("-" * 90)

        for row in rows:
            self.stdout.write(
                f"{row['status']:<12} "
                f"{row['scope']:<18} "
                f"{row['client']:<18} "
                f"{row['attempts']}/{row['limit']} per {row['window']:<12} "
                f"{row['remaining']:<10} "
                f"{row['retry_after']}"
            )
