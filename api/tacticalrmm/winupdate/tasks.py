import asyncio
import datetime as dt
import time

import pytz
from agents.models import Agent
from django.utils import timezone as djangotime
from logs.models import DebugLog
from packaging import version as pyver

from tacticalrmm.celery import app


@app.task
def auto_approve_updates_task() -> None:
    # scheduled task that checks and approves updates daily

    agents = Agent.objects.only(
        "pk", "agent_id", "version", "last_seen", "overdue_time", "offline_time"
    )
    for agent in agents:
        agent.delete_superseded_updates()
        try:
            agent.approve_updates()
        except:
            continue

    online = [
        i
        for i in agents
        if i.status == "online" and pyver.parse(i.version) >= pyver.parse("1.3.0")
    ]

    chunks = (online[i : i + 40] for i in range(0, len(online), 40))
    for chunk in chunks:
        for agent in chunk:
            asyncio.run(agent.nats_cmd({"func": "getwinupdates"}, wait=False))
            time.sleep(0.05)
        time.sleep(15)


@app.task
def check_agent_update_schedule_task() -> None:
    # scheduled task that installs updates on agents if enabled
    agents = Agent.objects.only(
        "pk",
        "agent_id",
        "version",
        "last_seen",
        "overdue_time",
        "offline_time",
        "has_patches_pending",
    )
    online = [
        i
        for i in agents
        if pyver.parse(i.version) >= pyver.parse("1.3.0")
        and i.has_patches_pending
        and i.status == "online"
    ]

    for agent in online:
        agent.delete_superseded_updates()
        install = False
        patch_policy = agent.get_patch_policy()

        # check if auto approval is enabled
        if (
            patch_policy.critical == "approve"
            or patch_policy.important == "approve"
            or patch_policy.moderate == "approve"
            or patch_policy.low == "approve"
            or patch_policy.other == "approve"
        ):

            # get current time in agent local time
            timezone = pytz.timezone(agent.timezone)
            agent_localtime_now = dt.datetime.now(timezone)
            weekday = agent_localtime_now.weekday()
            hour = agent_localtime_now.hour
            day = agent_localtime_now.day

            if agent.patches_last_installed:
                # get agent last installed time in local time zone
                last_installed = agent.patches_last_installed.astimezone(timezone)

                # check if patches were already run for this cycle and exit if so
                if last_installed.strftime("%d/%m/%Y") == agent_localtime_now.strftime(
                    "%d/%m/%Y"
                ):
                    return

            # check if schedule is set to daily/weekly and if now is the time to run
            if (
                patch_policy.run_time_frequency == "daily"
                and weekday in patch_policy.run_time_days
                and patch_policy.run_time_hour == hour
            ):
                install = True

            elif patch_policy.run_time_frequency == "monthly":

                if patch_policy.run_time_day > 28:
                    months_with_30_days = [3, 6, 9, 11]
                    current_month = agent_localtime_now.month
                    if current_month == 2:
                        patch_policy.run_time_day = 28
                    elif current_month in months_with_30_days:
                        patch_policy.run_time_day = 30

                # check if patches were scheduled to run today and now
                if (
                    day == patch_policy.run_time_day
                    and patch_policy.run_time_hour == hour
                ):
                    install = True

            if install:
                # initiate update on agent asynchronously and don't worry about ret code
                DebugLog.info(
                    agent=agent,
                    log_type="windows_updates",
                    message=f"Installing windows updates on {agent.hostname}",
                )
                nats_data = {
                    "func": "installwinupdates",
                    "guids": agent.get_approved_update_guids(),
                }
                asyncio.run(agent.nats_cmd(nats_data, wait=False))
                agent.patches_last_installed = djangotime.now()
                agent.save(update_fields=["patches_last_installed"])


@app.task
def bulk_install_updates_task(pks: list[int]) -> None:
    q = Agent.objects.filter(pk__in=pks)
    agents = [i for i in q if pyver.parse(i.version) >= pyver.parse("1.3.0")]
    chunks = (agents[i : i + 40] for i in range(0, len(agents), 40))
    for chunk in chunks:
        for agent in chunk:
            agent.delete_superseded_updates()
            try:
                agent.approve_updates()
            except:
                pass
            nats_data = {
                "func": "installwinupdates",
                "guids": agent.get_approved_update_guids(),
            }
            asyncio.run(agent.nats_cmd(nats_data, wait=False))
            time.sleep(0.05)
        time.sleep(15)


@app.task
def bulk_check_for_updates_task(pks: list[int]) -> None:
    q = Agent.objects.filter(pk__in=pks)
    agents = [i for i in q if pyver.parse(i.version) >= pyver.parse("1.3.0")]
    chunks = (agents[i : i + 40] for i in range(0, len(agents), 40))
    for chunk in chunks:
        for agent in chunk:
            agent.delete_superseded_updates()
            asyncio.run(agent.nats_cmd({"func": "getwinupdates"}, wait=False))
            time.sleep(0.05)
        time.sleep(15)
