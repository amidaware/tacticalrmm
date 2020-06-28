import os
import subprocess
from loguru import logger
from time import sleep
import requests


from django.conf import settings


from tacticalrmm.celery import app
from agents.models import Agent, AgentOutage

logger.configure(**settings.LOG_CONFIG)


@app.task
def get_wmi_detail_task(pk):
    agent = Agent.objects.get(pk=pk)
    r = agent.salt_api_cmd(timeout=30, func="win_agent.system_info")
    if r == "timeout" or r == "error":
        return "failed"

    agent.wmi_detail = r
    agent.save(update_fields=["wmi_detail"])
    return "ok"


@app.task
def sync_salt_modules_task(pk):
    agent = Agent.objects.get(pk=pk)
    r = agent.salt_api_cmd(timeout=35, func="saltutil.sync_modules")
    # successful sync if new/charnged files: {'return': [{'MINION-15': ['modules.get_eventlog', 'modules.win_agent', 'etc...']}]}
    # successful sync with no new/changed files: {'return': [{'MINION-15': []}]}
    if r == "timeout" or r == "error":
        logger.error(f"Unable to sync modules {agent.salt_id}")
        return

    logger.info(f"Successfully synced salt modules on {agent.hostname}")
    return "ok"


@app.task
def uninstall_agent_task(salt_id):
    attempts = 0
    error = False

    while 1:
        try:

            r = requests.post(
                f"http://{settings.SALT_HOST}:8123/run",
                json=[
                    {
                        "client": "local",
                        "tgt": salt_id,
                        "fun": "win_agent.uninstall_agent",
                        "timeout": 8,
                        "username": settings.SALT_USERNAME,
                        "password": settings.SALT_PASSWORD,
                        "eauth": "pam",
                    }
                ],
                timeout=10,
            )
            ret = r.json()["return"][0][salt_id]
        except Exception:
            attempts += 1
        else:
            if ret != "ok":
                attempts += 1
            else:
                attempts = 0

        if attempts >= 10:
            error = True
            break
        elif attempts == 0:
            break

    if error:
        logger.error(f"{salt_id} uninstall failed")
    else:
        logger.info(f"{salt_id} was successfully uninstalled")

    try:
        r = requests.post(
            f"http://{settings.SALT_HOST}:8123/run",
            json=[
                {
                    "client": "wheel",
                    "fun": "key.delete",
                    "match": salt_id,
                    "username": settings.SALT_USERNAME,
                    "password": settings.SALT_PASSWORD,
                    "eauth": "pam",
                }
            ],
            timeout=30,
        )
    except Exception:
        logger.error(f"{salt_id} unable to remove salt-key")

    return "ok"


@app.task
def update_agent_task(pk, version):

    agent = Agent.objects.get(pk=pk)

    def _service_action(action, service):
        return agent.salt_api_cmd(
            timeout=30,
            func="cmd.script",
            arg="C:\\Program Files\\TacticalAgent\\nssm.exe",
            kwargs={"args": f"{action} {service}"},
        )

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
        timeout=300,
        func="cp.get_file",
        arg=[f"salt://scripts/{version}.exe", temp_dir],
    )
    # success return example: {'return': [{'HOSTNAME': 'C:\\Windows\\Temp\\winagent-v0.1.12.exe'}]}
    # error return example: {'return': [{'HOSTNAME': ''}]}
    if r == "timeout" or r == "error":
        logger.error(
            f"{agent.hostname} update failed to version {ver} (unable to copy installer)"
        )
        return

    if not r:
        agent.is_updating = False
        agent.save(update_fields=["is_updating"])
        logger.error(
            f"{agent.hostname} update failed to version {ver} (unable to copy installer)"
        )
        return

    services = (
        "tacticalagent",
        "checkrunner",
    )

    for svc in services:
        r = _service_action("stop", svc)
        # returns non 0 if error
        if r["retcode"] != 0:
            errors.append(f"failed to stop {svc}")
            logger.error(
                f"{agent.hostname} was unable to stop service {svc}. Update cancelled"
            )

    # start the services if some of them failed to stop, then don't continue
    if errors:
        agent.is_updating = False
        agent.save(update_fields=["is_updating"])
        for svc in services:
            _service_action("start", svc)
        return

    # install the update
    # success respose example: {'return': [{'HOSTNAME': {'retcode': 0, 'stderr': '', 'stdout': '', 'pid': 3452}}]}
    # error response example: {'return': [{'HOSTNAME': 'The minion function caused an exception: Traceback...'}]}
    r = agent.salt_api_cmd(
        timeout=200,
        func="cmd.script",
        arg=f"{temp_dir}\\{version}.exe",
        kwargs={"args": "/VERYSILENT /SUPPRESSMSGBOXES"},
    )
    if r == "timeout" or r == "error":
        agent.is_updating = False
        agent.save(update_fields=["is_updating"])
        logger.error(
            f"TIMEOUT: failed to run inno setup on {agent.hostname} for version {ver}"
        )
        return

    if "minion function caused an exception" in r:
        agent.is_updating = False
        agent.save(update_fields=["is_updating"])
        logger.error(
            f"EXCEPTION: failed to run inno setup on {agent.hostname} for version {ver}"
        )
        return

    if r["retcode"] != 0:
        agent.is_updating = False
        agent.save(update_fields=["is_updating"])
        logger.error(f"failed to run inno setup on {agent.hostname} for version {ver}")
        return f"failed to run inno setup on {agent.hostname} for version {ver}"

    # update the version in the agent's local database
    r = agent.salt_api_cmd(
        timeout=30,
        func="sqlite3.modify",
        arg=[
            "C:\\Program Files\\TacticalAgent\\agentdb.db",
            f'UPDATE agentstorage SET version = "{ver}"',
        ],
    )
    # success return example: {'return': [{'FSV': True}]}
    # error return example: {'return': [{'HOSTNAME': 'The minion function caused an exception: Traceback...'}]}
    if r == "timeout" or r == "error":
        logger.error(f"failed to update {agent.hostname} local database")

    elif not isinstance(r, bool) and isinstance(r, str):
        if "minion function caused an exception" in r:
            logger.error(f"failed to update {agent.hostname} local database")

    elif isinstance(r, bool) and not r:
        logger.error(
            f"failed to update {agent.hostname} local database to version {ver}"
        )

    # start the services
    for svc in services:
        _service_action("start", svc)

    agent.is_updating = False
    agent.save(update_fields=["is_updating"])
    logger.info(f"{agent.hostname} was successfully updated to version {ver}")
    return "ok"


@app.task
def agent_outage_email_task(pk):
    outage = AgentOutage.objects.get(pk=pk)
    outage.send_outage_email()
    outage.outage_email_sent = True
    outage.save(update_fields=["outage_email_sent"])


@app.task
def agent_recovery_email_task(pk):
    outage = AgentOutage.objects.get(pk=pk)
    outage.send_recovery_email()
    outage.recovery_email_sent = True
    outage.save(update_fields=["recovery_email_sent"])


@app.task
def agent_outages_task():
    agents = Agent.objects.only("pk")

    for agent in agents:
        if agent.status == "overdue":
            outages = AgentOutage.objects.filter(agent=agent)
            if outages and outages.last().is_active:
                continue

            outage = AgentOutage(agent=agent)
            outage.save()

            if agent.overdue_email_alert:
                agent_outage_email_task.delay(pk=outage.pk)

            if agent.overdue_text_alert:
                # TODO
                pass
