import calendar
from zoneinfo import ZoneInfo

from tacticalrmm.constants import (
    MONTH_DAYS,
    WEEKS,
)
from tacticalrmm.helpers import is_month_in_bitmask, is_weekday_in_bitmask


def should_run_daily_task(task, agent, current_time) -> bool:

    agent_timezone = ZoneInfo(agent.timezone)
    current_time_agent_tz = current_time.astimezone(agent_timezone)

    current_hour = current_time_agent_tz.hour
    current_minute = current_time_agent_tz.minute

    run_hour = task.run_time_date.hour
    run_minute = task.run_time_date.minute

    return (current_hour == run_hour) and (current_minute == run_minute)


def should_run_once_task(task, agent, current_time) -> bool:

    agent_timezone = ZoneInfo(agent.timezone)
    current_time_agent_tz = current_time.astimezone(agent_timezone)

    task_time_naive = task.run_time_date.replace(tzinfo=agent_timezone)

    task_time_rounded = task_time_naive.replace(second=0, microsecond=0)
    current_time_rounded = current_time_agent_tz.replace(second=0, microsecond=0)

    return task_time_rounded == current_time_rounded


def should_run_weekly_task(task, agent, current_time) -> bool:

    agent_timezone = ZoneInfo(agent.timezone)
    current_time_agent_tz = current_time.astimezone(agent_timezone)

    current_hour = current_time_agent_tz.hour
    current_minute = current_time_agent_tz.minute

    run_hour = task.run_time_date.hour
    run_minute = task.run_time_date.minute

    if is_weekday_in_bitmask(
        current_time_agent_tz.weekday(), task.run_time_bit_weekdays
    ):
        return (current_hour == run_hour) and (current_minute == run_minute)

    return False


def should_run_monthly_dow_task(task, agent, current_time) -> bool:
    agent_timezone = ZoneInfo(agent.timezone)
    current_time_agent_tz = current_time.astimezone(agent_timezone)

    current_hour = current_time_agent_tz.hour
    current_minute = current_time_agent_tz.minute

    run_hour = task.run_time_date.hour
    run_minute = task.run_time_date.minute

    weekday = current_time_agent_tz.weekday()
    month = current_time_agent_tz.month
    day = current_time_agent_tz.day
    year = current_time_agent_tz.year

    if not is_weekday_in_bitmask(weekday, task.run_time_bit_weekdays):
        return False

    if not is_month_in_bitmask(month, task.monthly_months_of_year):
        return False

    # fist week: 1-7, 2nd week: 8-14, 3rd week: 15-21, 4th week: 22-28, last week: 29-end
    # TODO fix last week
    week_num = (day - 1) // 7 + 1
    total_days = calendar.monthrange(year, month)[1]
    last_week_num = (total_days - 1) // 7 + 1

    if week_num == last_week_num:
        week_bit = WEEKS["Last Week"]
    else:
        week_key = ["First Week", "Second Week", "Third Week", "Fourth Week"][
            week_num - 1
        ]
        week_bit = WEEKS[week_key]

    if not (week_bit & task.monthly_weeks_of_month):
        return False

    return (current_hour == run_hour) and (current_minute == run_minute)


def should_run_monthly_task(task, agent, current_time) -> bool:

    agent_timezone = ZoneInfo(agent.timezone)
    current_time_agent_tz = current_time.astimezone(agent_timezone)

    current_month = current_time_agent_tz.month
    current_day = current_time_agent_tz.day
    current_hour = current_time_agent_tz.hour
    current_minute = current_time_agent_tz.minute

    run_hour = task.run_time_date.hour
    run_minute = task.run_time_date.minute

    if not is_month_in_bitmask(current_month, task.monthly_months_of_year):
        return False

    last_day_of_month = calendar.monthrange(current_time_agent_tz.year, current_month)[
        1
    ]
    if current_day == last_day_of_month:
        if task.monthly_days_of_month & MONTH_DAYS["Last Day"]:
            return (current_hour == run_hour) and (current_minute == run_minute)

    if task.monthly_days_of_month & MONTH_DAYS.get(str(current_day), 0):
        return (current_hour == run_hour) and (current_minute == run_minute)

    return False
