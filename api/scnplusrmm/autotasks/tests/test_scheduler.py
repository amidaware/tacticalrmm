import datetime as dt
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.conf import settings
from django.utils import timezone as djangotime
from model_bakery import baker

from core.tasks import scheduled_task_runner
from tacticalrmm.constants import AgentPlat, TaskSyncStatus, TaskType

utc_time = ZoneInfo("UTC")
los_angeles = ZoneInfo("America/Los_Angeles")


@pytest.fixture
def setup_instance(db):
    client1 = baker.make("clients.Client")
    site1 = baker.make("clients.Site", client=client1)
    baker.make("core.CoreSettings")

    now = djangotime.now()

    tasks_data = [
        {
            "task_type": TaskType.DAILY,
            "run_time": dt.datetime(2025, 3, 22, 11, 33, tzinfo=utc_time),
        },
        {
            "task_type": TaskType.WEEKLY,
            "run_time": dt.datetime(
                2025, 4, 13, 17, 55, tzinfo=utc_time
            ),  # not tuesday, date should not matter
            "weekly_bit": 4,  # tuesday
        },
        {
            "task_type": TaskType.MONTHLY,
            "run_time": dt.datetime(2029, 4, 22, 1, 23, tzinfo=utc_time),
            "months_of_year": 804,  # march, june, sept, oct
            "days_of_month": 268967936,  # 14, 20, 29
        },
        {
            "task_type": TaskType.MONTHLY_DOW,
            "run_time": dt.datetime(2029, 4, 22, 18, 32, tzinfo=utc_time),
            "months_of_year": 145,  # jan, may, aug
            "on_weeks": 16,  # last week of the month
            "on_days": 32,  # friday
        },
        {
            "task_type": TaskType.MONTHLY_DOW,
            "run_time": dt.datetime(2029, 4, 22, 17, 11, tzinfo=utc_time),
            "months_of_year": 72,  # april, july
            "on_weeks": 22,  # second, thirt and last weeks of month
            "on_days": 50,  # monday, thursday, friday
        },
    ]

    data = [
        {
            "plat": AgentPlat.WINDOWS,
            "agent_id": "windows-agent-id",
            "tasks": tasks_data,
        },
        {
            "plat": AgentPlat.LINUX,
            "agent_id": "windows-linux-id",
            "tasks": tasks_data,
        },
        {
            "plat": AgentPlat.DARWIN,
            "agent_id": "windows-darwin-id",
            "tasks": tasks_data,
        },
    ]

    for item in data:
        agent = baker.make(
            "agents.Agent",
            site=site1,
            plat=item["plat"],
            last_seen=now,
            version=settings.LATEST_AGENT_VER,
            agent_id=item["agent_id"],
        )

        for task in item["tasks"]:
            t = baker.make(
                "autotasks.AutomatedTask",
                agent=agent,
                task_type=task["task_type"],
                run_time_date=task["run_time"],
            )

            if t.task_type == TaskType.WEEKLY:
                t.run_time_bit_weekdays = task["weekly_bit"]
                t.save()
            elif t.task_type == TaskType.MONTHLY:
                t.monthly_months_of_year = task["months_of_year"]
                t.monthly_days_of_month = task["days_of_month"]
                t.save()
            elif t.task_type == TaskType.MONTHLY_DOW:
                t.monthly_months_of_year = task["months_of_year"]
                t.monthly_weeks_of_month = task["on_weeks"]
                t.run_time_bit_weekdays = task["on_days"]
                t.save()

            baker.make(
                "autotasks.TaskResult",
                agent=agent,
                task=t,
                sync_status=TaskSyncStatus.SYNCED,
            )


@pytest.fixture
def mock_abulk_nats_command():
    with patch("core.tasks.abulk_nats_command", new_callable=AsyncMock) as mock_func:
        mock_func.return_value = None
        yield mock_func


# only posix agents should run these tasks


@time_machine.travel(dt.datetime(2025, 3, 22, 11, 33, tzinfo=los_angeles))
@pytest.mark.django_db
def test_daily_task(setup_instance, mock_abulk_nats_command):
    ret = scheduled_task_runner()
    mock_abulk_nats_command.assert_called_once()
    assert len(ret) == 2


@time_machine.travel(dt.datetime(2025, 4, 15, 17, 55, tzinfo=los_angeles))  # tuesday
@pytest.mark.django_db
def test_weekly_task(setup_instance, mock_abulk_nats_command):
    ret = scheduled_task_runner()
    mock_abulk_nats_command.assert_called_once()
    assert len(ret) == 2


@time_machine.travel(dt.datetime(2025, 9, 20, 1, 23, tzinfo=los_angeles))
@pytest.mark.django_db
def test_monthly_task_sept_20(setup_instance, mock_abulk_nats_command):
    ret = scheduled_task_runner()
    mock_abulk_nats_command.assert_called_once()
    assert len(ret) == 2


@time_machine.travel(dt.datetime(2025, 6, 14, 1, 23, tzinfo=los_angeles))
@pytest.mark.django_db
def test_monthly_task_june_14(setup_instance, mock_abulk_nats_command):
    ret = scheduled_task_runner()
    mock_abulk_nats_command.assert_called_once()
    assert len(ret) == 2


@time_machine.travel(dt.datetime(2025, 6, 15, 1, 23, tzinfo=los_angeles))
@pytest.mark.django_db
def test_monthly_task_june_15(setup_instance, mock_abulk_nats_command):
    ret = scheduled_task_runner()
    mock_abulk_nats_command.assert_not_called()
    assert len(ret) == 0


@time_machine.travel(
    dt.datetime(2026, 1, 30, 18, 32, tzinfo=los_angeles)
)  # friday jan 30, 2026 falls in the last week of the month
@pytest.mark.django_db
def test_monthly_DOW(setup_instance, mock_abulk_nats_command):
    ret = scheduled_task_runner()
    mock_abulk_nats_command.assert_called_once()
    assert len(ret) == 2


@time_machine.travel(
    dt.datetime(2025, 7, 10, 17, 11, tzinfo=los_angeles)
)  # thurs july 10, 2025 falls in the 2nd week of the month
@pytest.mark.django_db
def test_monthly_DOW_2(setup_instance, mock_abulk_nats_command):
    ret = scheduled_task_runner()
    mock_abulk_nats_command.assert_called_once()
    assert len(ret) == 2


@time_machine.travel(
    dt.datetime(2025, 7, 3, 17, 11, tzinfo=los_angeles)
)  # thurs july 3, 2025 falls in the 1st week of the month, should fail
@pytest.mark.django_db
@patch("asyncio.run")
def test_monthly_DOW_3(setup_instance, mock_abulk_nats_command):
    ret = scheduled_task_runner()
    mock_abulk_nats_command.assert_not_called()
    assert len(ret) == 0
