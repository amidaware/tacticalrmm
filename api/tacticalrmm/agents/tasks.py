import os
import subprocess
from loguru import logger
from time import sleep

from tacticalrmm.celery import app
from django.conf import settings

from agents.models import Agent

logger.configure(**settings.LOG_CONFIG)


@app.task
def get_wmi_detail_task(pk):
    agent = Agent.objects.get(pk=pk)
    resp = agent.salt_api_cmd(
        hostname=agent.salt_id, timeout=30, func="system_info.system_info"
    )
    agent.wmi_detail = resp.json()["return"][0][agent.salt_id]
    agent.save(update_fields=["wmi_detail"])
    return "ok"


@app.task
def sync_salt_modules_task(pk):
    agent = Agent.objects.get(pk=pk)

    resp = agent.salt_api_cmd(
        hostname=agent.salt_id, timeout=60, func="saltutil.sync_modules"
    )
    # successful sync if new/charnged files: {'return': [{'MINION-15': ['modules.get_eventlog', 'modules.win_agent', 'etc...']}]}
    # successful sync with no new/changed files: {'return': [{'MINION-15': []}]}
    try:
        data = resp.json()["return"][0][agent.salt_id]
    except Exception as f:
        logger.error(f"Unable to sync modules {agent.salt_id}: {f}")
        return f"Unable to sync modules {agent.salt_id}: {f}"
    else:
        logger.info(f"Successfully synced salt modules on {agent.hostname}")
        return f"Successfully synced salt modules on {agent.hostname}"


@app.task
def uninstall_agent_task(pk, wait=True):
    agent = Agent.objects.get(pk=pk)
    agent.uninstall_inprogress = True
    agent.save(update_fields=["uninstall_inprogress"])
    logger.info(f"{agent.hostname} uninstall task is running")

    if wait:
        logger.info(f"{agent.hostname} waiting 90 seconds before uninstalling")
        sleep(90)  # need to give salt time to startup on the minion

    resp2 = agent.salt_api_cmd(
        hostname=agent.salt_id,
        timeout=60,
        func="cp.get_file",
        arg=["salt://scripts/removeagent.exe", "C:\\Windows\\Temp\\"],
    )
    data2 = resp2.json()
    if not data2["return"][0][agent.salt_id]:
        logger.error(f"{agent.hostname} unable to copy file")
        return f"{agent.hostname} unable to copy file"

    agent.salt_api_cmd(
        hostname=agent.salt_id,
        timeout=500,
        func="cmd.script",
        arg="salt://scripts/uninstall.bat",
    )

    logger.info(f"{agent.hostname} was successfully uninstalled")
    return f"{agent.hostname} was successfully uninstalled"


def service_action(hostname, action, service):
    return Agent.salt_api_cmd(
        hostname=hostname,
        timeout=30,
        func="cmd.script",
        arg="C:\\Program Files\\TacticalAgent\\nssm.exe",
        kwargs={"args": f"{action} {service}"},
    )


@app.task
def update_agent_task(pk, version):

    agent = Agent.objects.get(pk=pk)

    errors = []
    file = f"/srv/salt/scripts/{version}.exe"
    ver = version.split("winagent-v")[1]

    # download the release from github if the file doesn't already exist in /srv
    if not os.path.exists(file):
        r = Agent.get_github_versions()
        git_versions = r["versions"]
        data = r["data"]  # full response from github
        versions = {}

        for i, release in enumerate(data):
            versions[i] = release["name"]

        key = [k for k, v in versions.items() if v == version][0]

        download_url = data[key]["assets"][0]["browser_download_url"]

        p = subprocess.run(["wget", download_url, "-O", file], capture_output=True)

    app_dir = "C:\\Program Files\\TacticalAgent"
    temp_dir = "C:\\Windows\\Temp"

    logger.info(
        f"{agent.hostname} is attempting update from version {agent.version} to {ver}"
    )

    # send the release to the agent
    r = agent.salt_api_cmd(
        hostname=agent.salt_id,
        timeout=300,
        func="cp.get_file",
        arg=[f"salt://scripts/{version}.exe", temp_dir],
    )
    # success return example: {'return': [{'HOSTNAME': 'C:\\Windows\\Temp\\winagent-v0.1.12.exe'}]}
    # error return example: {'return': [{'HOSTNAME': ''}]}
    if not r.json()["return"][0][agent.salt_id]:
        agent.is_updating = False
        agent.save(update_fields=["is_updating"])
        logger.error(
            f"{agent.hostname} update failed to version {ver} (unable to copy installer)"
        )
        return f"{agent.hostname} update failed to version {ver} (unable to copy installer)"

    services = (
        "tacticalagent",
        "checkrunner",
        "winupdater",
    )

    for svc in services:
        r = service_action(agent.salt_id, "stop", svc)
        # returns non 0 if error
        if r.json()["return"][0][agent.salt_id]["retcode"]:
            errors.append(f"failed to stop {svc}")
            logger.error(
                f"{agent.hostname} was unable to stop service {svc}. Update cancelled"
            )

    # start the services if some of them failed to stop, then don't continue
    if errors:
        agent.is_updating = False
        agent.save(update_fields=["is_updating"])
        for svc in services:
            service_action(agent.salt_id, "start", svc)
        return "stopping services failed. started again"

    # install the update
    # success respose example: {'return': [{'HOSTNAME': {'retcode': 0, 'stderr': '', 'stdout': '', 'pid': 3452}}]}
    # error response example: {'return': [{'HOSTNAME': 'The minion function caused an exception: Traceback...'}]}
    try:
        r = agent.salt_api_cmd(
            hostname=agent.salt_id,
            timeout=200,
            func="cmd.script",
            arg=f"{temp_dir}\\{version}.exe",
            kwargs={"args": "/VERYSILENT /SUPPRESSMSGBOXES"},
        )
    except Exception:
        agent.is_updating = False
        agent.save(update_fields=["is_updating"])
        return (
            f"TIMEOUT: failed to run inno setup on {agent.hostname} for version {ver}"
        )

    if "minion function caused an exception" in r.json()["return"][0][agent.salt_id]:
        agent.is_updating = False
        agent.save(update_fields=["is_updating"])
        return (
            f"EXCEPTION: failed to run inno setup on {agent.hostname} for version {ver}"
        )

    if r.json()["return"][0][agent.salt_id]["retcode"]:
        agent.is_updating = False
        agent.save(update_fields=["is_updating"])
        logger.error(f"failed to run inno setup on {agent.hostname} for version {ver}")
        return f"failed to run inno setup on {agent.hostname} for version {ver}"

    # update the version in the agent's local database
    r = agent.salt_api_cmd(
        hostname=agent.salt_id,
        timeout=45,
        func="sqlite3.modify",
        arg=[
            "C:\\Program Files\\TacticalAgent\\agentdb.db",
            f'UPDATE agentstorage SET version = "{ver}"',
        ],
    )
    # success return example: {'return': [{'FSV': True}]}
    # error return example: {'return': [{'HOSTNAME': 'The minion function caused an exception: Traceback...'}]}
    sql_ret = type(r.json()["return"][0][agent.salt_id])
    if sql_ret is not bool and sql_ret is str:
        if (
            "minion function caused an exception"
            in r.json()["return"][0][agent.salt_id]
        ):
            logger.error(f"failed to update {agent.hostname} local database")

    if not r.json()["return"][0][agent.salt_id]:
        logger.error(
            f"failed to update {agent.hostname} local database to version {ver}"
        )

    # start the services
    for svc in services:
        service_action(agent.salt_id, "start", svc)

    agent.is_updating = False
    agent.save(update_fields=["is_updating"])
    logger.info(f"{agent.hostname} was successfully updated to version {ver}")
    return f"{agent.hostname} was successfully updated to version {ver}"
