import pytest
from datetime import time, datetime
from zoneinfo import ZoneInfo
import time_machine

from tacticalrmm.scheduler import (
    should_run_daily,
    should_run_weekly,
    should_run_monthly,
    should_run_monthly_dow,
    LAST_DAY_OF_MONTH,
    LAST_WEEK_OF_MONTH,
)

@pytest.fixture
def run_time_10am():
    return time(10, 0)

@pytest.fixture
def est_timezone():
    return ZoneInfo("America/New_York")

# daily
def test_should_run_daily_exact_time(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2023-10-27 14:00:00+00:00") # 10:00 AM in New York
    assert should_run_daily(
        run_time=run_time_10am,
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )

def test_should_not_run_daily_off_time(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2023-10-27 14:01:00+00:00")
    assert not should_run_daily(
        run_time=run_time_10am,
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )

# weekly
def test_should_run_weekly_correct_day_and_time(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2023-10-27 14:00:00+00:00") # Friday 10:00 AM in New York
    assert should_run_weekly(
        run_time=run_time_10am,
        weekdays=[0, 2, 4],
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )

def test_should_not_run_weekly_incorrect_day(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2023-10-26 14:00:00+00:00") # Thursday 10:00 AM in New York
    assert not should_run_weekly(
        run_time=run_time_10am,
        weekdays=[0, 2, 4],
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )

# monthly
def test_should_run_monthly_correct_day(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2023-10-15 14:00:00+00:00")
    assert should_run_monthly(
        run_time=run_time_10am,
        days=[1, 15],
        months=[10, 12],
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )

def test_should_not_run_monthly_incorrect_month(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2023-11-15 15:00:00+00:00")
    assert not should_run_monthly(
        run_time=run_time_10am,
        days=[1, 15],
        months=[10, 12],
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )

def test_should_run_monthly_last_day_of_month(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2023-10-31 14:00:00+00:00")
    assert should_run_monthly(
        run_time=run_time_10am,
        days=[LAST_DAY_OF_MONTH],
        months=[10],
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )

def test_should_run_monthly_last_day_of_leap_year_february(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2024-02-29 15:00:00+00:00")
    assert should_run_monthly(
        run_time=run_time_10am,
        days=[LAST_DAY_OF_MONTH],
        months=[2],
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )

# monthly dow
def test_should_run_monthly_dow_correct_week_and_day(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2023-10-27 14:00:00+00:00") # 4th Friday in New York
    assert should_run_monthly_dow(
        run_time=run_time_10am,
        weekdays=[4],
        weeks=[4],
        months=[10],
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )

def test_should_run_monthly_dow_last_week_of_month(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2023-10-31 14:00:00+00:00") # Last Tuesday in New York
    assert should_run_monthly_dow(
        run_time=run_time_10am,
        weekdays=[1],
        weeks=[LAST_WEEK_OF_MONTH],
        months=[10],
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )

def test_should_not_run_monthly_dow_incorrect_week(time_machine, run_time_10am, est_timezone):
    time_machine.move_to("2023-10-20 14:00:00+00:00") # 3rd Friday in New York
    assert not should_run_monthly_dow(
        run_time=run_time_10am,
        weekdays=[4],
        weeks=[4],
        months=[10],
        current_time=datetime.now(ZoneInfo("UTC")),
        timezone=est_timezone,
    )