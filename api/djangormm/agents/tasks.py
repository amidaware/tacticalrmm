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
                if data2["return"][0][agent.hostname]:
                    logger.info(f"Successfully synced salt modules on {agent.hostname}")
                    return f"Successfully synced salt modules on {agent.hostname}"
                else:
                    logger.critical(f"Failed to sync salt modules on {agent.hostname}")
                    return f"Failed to sync salt modules on {agent.hostname}"



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