import asyncio
from loguru import logger
from tacticalrmm.celery import app
from django.conf import settings

from agents.models import Agent
from .models import ChocoLog

logger.configure(**settings.LOG_CONFIG)


@app.task
def install_program(pk, name, version):
    agent = Agent.objects.get(pk=pk)
    nats_data = {
        "func": "installwithchoco",
        "choco_prog_name": name,
        "choco_prog_ver": version,
    }
    r: str = asyncio.run(agent.nats_cmd(nats_data, timeout=915))
    if r == "timeout":
        logger.error(f"Failed to install {name} {version} on {agent.salt_id}: timeout")
        return

    try:
        output = r.lower()
    except Exception as e:
        logger.error(f"Failed to install {name} {version} on {agent.salt_id}: {e}")
        return

    success = [
        "install",
        "of",
        name.lower(),
        "was",
        "successful",
        "installed",
    ]
    duplicate = [name.lower(), "already", "installed", "--force", "reinstall"]

    installed = False

    if all(x in output for x in success):
        installed = True
        logger.info(f"Successfully installed {name} {version} on {agent.salt_id}")
    elif all(x in output for x in duplicate):
        logger.warning(f"Already installed: {name} {version} on {agent.salt_id}")
    else:
        logger.error(f"Something went wrong - {name} {version} on {agent.salt_id}")

    ChocoLog(
        agent=agent, name=name, version=version, message=output, installed=installed
    ).save()

    return "ok"
