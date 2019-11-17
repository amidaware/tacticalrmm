from loguru import logger
from time import sleep

from djangormm.celery import app
from django.conf import settings

from agents.models import Agent

logger.configure(**settings.LOG_CONFIG)

@app.task
def sync_salt_modules_task(pk):
    agent = Agent.objects.get(pk=pk)
    logger.info(f"Attempting to sync salt modules on {agent.hostname}")
    sleep(10)
    resp = agent.salt_api_cmd(
        hostname=agent.hostname,
        timeout=30,
        func="test.ping"
    )
    try:
        data = resp.json()
    except Exception as e:
        logger.error(f"Unable to contact agent {agent.hostname}: {e}")
        return f"Unable to contact agent {agent.hostname}: {e}"
    else:
        try: 
            ping = data["return"][0][agent.hostname]
        except KeyError as j:
            logger.error(f"{j}: Unable to contact agent (is salt installed properly?)")
            return f"{j}: Unable to contact agent (is salt installed properly?)"
        else:
            resp2 = agent.salt_api_cmd(
                hostname=agent.hostname,
                timeout=60,
                func="saltutil.sync_modules"
            )
            try:
                data2 = resp2.json()
            except Exception as f:
                logger.error(f"Unable to contact agent {agent.hostname}: {f}")
                return f"Unable to contact agent {agent.hostname}: {f}"
            else:
                # TODO fix return type
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
        sleep(90) # need to give salt time to startup on the minion

    resp2 = agent.salt_api_cmd(
        hostname=agent.hostname, 
        timeout=60, 
        func="cp.get_file", 
        arg=["salt://scripts/removeagent.exe", "C:\\Windows\\Temp\\"]
    )
    data2 = resp2.json()
    if not data2["return"][0][agent.hostname]:
        logger.error(f"{agent.hostname} unable to copy file")
        return f"{agent.hostname} unable to copy file"

    agent.salt_api_cmd(
        hostname=agent.hostname, 
        timeout=500, 
        func="cmd.script", 
        arg="salt://scripts/uninstall.bat"
    )
    
    logger.info(f"{agent.hostname} was successfully uninstalled")
    return f"{agent.hostname} was successfully uninstalled"


@app.task
def update_agent_task(pk, version="0.1.4"):
    app_dir = "C:\\Program Files\\TacticalAgent"
    temp_dir = "C:\\Windows\\Temp"
    agent = Agent.objects.get(pk=pk)
    logger.info(f"{agent.hostname} is updating")

    cp_installer = agent.salt_api_cmd(
        hostname=agent.hostname, 
        timeout=120, 
        func="cp.get_file", 
        arg=[f"salt://scripts/winagent-{version}.exe", temp_dir]
    )
    cp_resp = cp_installer.json()
    if not cp_resp["return"][0][agent.hostname]:
        logger.error(f"{agent.hostname} unable to copy installer")
        return f"{agent.hostname} unable to copy installer"

    
    resp1 = agent.salt_api_cmd(
        hostname=agent.hostname,
        timeout=45, 
        func="cmd.script", 
        arg=f"{app_dir}\\nssm.exe",
        kwargs={"args": "stop tacticalagent"}
    )
    data1 = resp1.json()
    if not data1["return"][0][agent.hostname]:
        logger.error(f"{agent.hostname} unable to stop tacticalagent service")
        return f"{agent.hostname} unable to stop tacticalagent service"
    

    resp2 = agent.salt_api_cmd(
        hostname=agent.hostname,
        timeout=45, 
        func="cmd.script", 
        arg=f"{app_dir}\\nssm.exe",
        kwargs={"args": "stop checkrunner"}
    )
    data2 = resp2.json()
    if not data2["return"][0][agent.hostname]:
        logger.error(f"{agent.hostname} unable to stop checkrunner service")
        return f"{agent.hostname} unable to stop checkrunner service"
    
    update_version = agent.salt_api_cmd(
        hostname=agent.hostname,
        timeout=45,
        func="sqlite3.modify",
        arg=[
            "C:\\Program Files\\TacticalAgent\\winagent\\agentdb.db",
            f'UPDATE agentstorage SET version = "{version}"'
        ]
    )
    versiondata = update_version.json()
    if not versiondata["return"][0][agent.hostname]:
        logger.error(f"{agent.hostname} unable to update sql version")
        return f"{agent.hostname} unable to update sql version"

    resp3 = agent.salt_api_cmd(
        hostname=agent.hostname,
        timeout=120, 
        func="cmd.script", 
        arg=f"{temp_dir}\\winagent-{version}.exe",
        kwargs={"args": "/VERYSILENT /SUPPRESSMSGBOXES"}
    )
    data3 = resp3.json()
    if not data3["return"][0][agent.hostname]:
        logger.error(f"{agent.hostname} unable to install the update")
        return f"{agent.hostname} unable to install the update"
    

    resp4 = agent.salt_api_cmd(
        hostname=agent.hostname,
        timeout=45, 
        func="cmd.script", 
        arg=f"{app_dir}\\nssm.exe",
        kwargs={"args": "start tacticalagent"}
    )
    data4 = resp4.json()
    if not data4["return"][0][agent.hostname]:
        logger.error(f"{agent.hostname} unable to start tacticalagent service")
        return f"{agent.hostname} unable to start tacticalagent service"
    

    resp5 = agent.salt_api_cmd(
        hostname=agent.hostname,
        timeout=45, 
        func="cmd.script", 
        arg=f"{app_dir}\\nssm.exe",
        kwargs={"args": "start checkrunner"}
    )
    data5 = resp5.json()
    if not data5["return"][0][agent.hostname]:
        logger.error(f"{agent.hostname} unable to start checkrunner service")
        return f"{agent.hostname} unable to start checkrunner service"
    
    

    
    logger.info(f"{agent.hostname} was successfully updated")
    return f"{agent.hostname} was successfully updated"