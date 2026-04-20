from datetime import datetime as dt
from itertools import cycle
from zoneinfo import ZoneInfo

from model_bakery.recipe import Recipe, seq

from .models import WinUpdate, WinUpdatePolicy

timezone = ZoneInfo("America/Los_Angeles")

severity = ["Critical", "Important", "Moderate", "Low", ""]
winupdate = Recipe(
    WinUpdate,
    kb=seq("kb0000000"),
    guid=seq("12312331-123232-123-123-1123123"),
    severity=cycle(severity),
)

winupdate_policy = Recipe(
    WinUpdatePolicy,
    run_time_hour=dt.now(timezone).hour,
    run_time_frequency="daily",
    run_time_days=[dt.now(timezone).weekday()],
)

winupdate_approve = winupdate_policy.extend(
    critical="approve",
    important="approve",
    moderate="approve",
    low="approve",
    other="approve",
)
