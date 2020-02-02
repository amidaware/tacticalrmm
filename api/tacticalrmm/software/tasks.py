from time import sleep
from loguru import logger
from tacticalrmm.celery import app
from django.conf import settings

from agents.models import Agent
from .models import ChocoSoftware, ChocoLog, InstalledSoftware

logger.configure(**settings.LOG_CONFIG)


@app.task()
def install_chocolatey(pk, wait=False):
    if wait:
        sleep(10)
    agent = Agent.objects.get(pk=pk)
    r = agent.salt_api_cmd(
        hostname=agent.salt_id,
        timeout=300,
        func="chocolatey.bootstrap",
        arg="force=True",
    )
    try:
        r.json()
    except Exception as e:
        return f"error installing choco on {agent.salt_id}"

    if type(r.json()) is dict:
        try:
            output = r.json()["return"][0][agent.salt_id].lower()
        except Exception:
            return f"error installing choco on {agent.salt_id}"

    success = ["chocolatey", "is", "now", "ready"]

    if all(x in output for x in success):
        agent.choco_installed = True
        agent.save(update_fields=["choco_installed"])
        logger.info(f"Installed chocolatey on {agent.salt_id}")
        return f"Installed choco on {agent.salt_id}"
    else:
        return f"error installing choco on {agent.salt_id}"


@app.task
def update_chocos():
    agents = Agent.objects.only("pk")
    online = [x for x in agents if x.status == "online" and x.choco_installed]

    while 1:
        for agent in online:
            try:
                ret = agent.salt_api_cmd(
                    hostname=agent.salt_id, timeout=15, func="test.ping"
                )
            except Exception:
                continue

            try:
                data = ret.json()["return"][0][agent.salt_id]
            except Exception:
                continue
            else:
                if data:
                    install = agent.salt_api_cmd(
                        hostname=agent.salt_id,
                        timeout=180,
                        func="chocolatey.bootstrap",
                        arg="force=True",
                    )
                    resp = agent.salt_api_cmd(
                        hostname=agent.salt_id, timeout=200, func="chocolatey.list"
                    )
                    ret = resp.json()["return"][0][agent.salt_id]

                    try:
                        chocos = [{"name": k, "version": v[0]} for k, v in ret.items()]
                    except AttributeError:
                        continue
                    else:
                        # somtimes chocolatey api is down or buggy and doesn't return the full list of software
                        if len(chocos) < 4000:
                            continue
                        else:
                            logger.info(
                                f"Chocos were updated using agent {agent.salt_id}"
                            )
                            ChocoSoftware(chocos=chocos).save()
                            break

        break

    return "ok"


@app.task
def get_installed_software(pk):
    agent = Agent.objects.get(pk=pk)
    r = agent.salt_api_cmd(hostname=agent.salt_id, timeout=30, func="pkg.list_pkgs")
    try:
        output = r.json()["return"][0][agent.salt_id]
    except Exception:
        logger.error(f"Unable to get installed software on {agent.salt_id}")
        return "error"

    try:
        software = [{"name": k, "version": v} for k, v in output.items()]
    except Exception:
        logger.error(f"Unable to get installed software on {agent.salt_id}")
        return "error"

    if not InstalledSoftware.objects.filter(agent=agent).exists():
        InstalledSoftware(agent=agent, software=software).save()
    else:
        current = InstalledSoftware.objects.filter(agent=agent).get()
        current.software = software
        current.save(update_fields=["software"])

    return "ok"


@app.task
def install_program(pk, name, version):
    agent = Agent.objects.get(pk=pk)

    r = agent.salt_api_cmd(
        hostname=agent.salt_id,
        timeout=1000,
        func="chocolatey.install",
        arg=[name, f"version={version}"],
    )
    try:
        r.json()
    except Exception as e:
        logger.error(f"Error installing {name} {version} on {agent.salt_id}: {e}")
        return "error"

    if type(r.json()) is dict:
        try:
            output = r.json()["return"][0][agent.salt_id].lower()
        except Exception as e:
            logger.error(f"Error installing {name} {version} on {agent.salt_id}: {e}")
            return "error"

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

    get_installed_software.delay(agent.pk)

    return "ok"
