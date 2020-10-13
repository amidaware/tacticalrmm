import string
from time import sleep
from loguru import logger
from tacticalrmm.celery import app
from django.conf import settings
from django.utils import timezone as djangotime

from agents.models import Agent
from .models import ChocoSoftware, ChocoLog, InstalledSoftware

logger.configure(**settings.LOG_CONFIG)


@app.task()
def install_chocolatey(pk, wait=False):
    if wait:
        sleep(15)

    agent = Agent.objects.get(pk=pk)
    r = agent.salt_api_cmd(timeout=120, func="chocolatey.bootstrap", arg="force=True")

    if r == "timeout" or r == "error":
        logger.error(f"failed to install choco on {agent.salt_id}")
        return

    try:
        output = r.lower()
    except Exception as e:
        logger.error(f"failed to install choco on {agent.salt_id}: {e}")
        return

    success = ["chocolatey", "is", "now", "ready"]

    if all(x in output for x in success):
        agent.choco_installed = True
        agent.save(update_fields=["choco_installed"])
        logger.info(f"Installed chocolatey on {agent.salt_id}")
        return "ok"
    else:
        logger.error(f"failed to install choco on {agent.salt_id}")
        return


@app.task
def update_chocos():
    # delete choco software older than 10 days
    try:
        first = ChocoSoftware.objects.first().pk
        q = ChocoSoftware.objects.exclude(pk=first).filter(
            added__lte=djangotime.now() - djangotime.timedelta(days=10)
        )
        q.delete()
    except:
        pass

    agents = Agent.objects.only("pk")
    online = [x for x in agents if x.status == "online" and x.choco_installed]

    while 1:
        for agent in online:

            r = agent.salt_api_cmd(timeout=10, func="test.ping")
            if r == "timeout" or r == "error" or (isinstance(r, bool) and not r):
                continue

            if isinstance(r, bool) and r:
                ret = agent.salt_api_cmd(timeout=200, func="chocolatey.list")
                if ret == "timeout" or ret == "error":
                    continue

                try:
                    chocos = [{"name": k, "version": v[0]} for k, v in ret.items()]
                except AttributeError:
                    continue
                else:
                    # somtimes chocolatey api is down or buggy and doesn't return the full list of software
                    if len(chocos) < 4000:
                        continue
                    else:
                        logger.info(f"Chocos were updated using {agent.salt_id}")
                        ChocoSoftware(chocos=chocos).save()
                        break

        break

    return "ok"


@app.task
def get_installed_software(pk):
    agent = Agent.objects.get(pk=pk)
    r = agent.salt_api_cmd(
        timeout=30,
        func="pkg.list_pkgs",
        kwargs={"include_components": False, "include_updates": False},
    )

    if r == "timeout" or r == "error":
        logger.error(f"Timed out trying to get installed software on {agent.salt_id}")
        return

    printable = set(string.printable)

    try:
        software = [
            {
                "name": "".join(filter(lambda x: x in printable, k)),
                "version": "".join(filter(lambda x: x in printable, v)),
            }
            for k, v in r.items()
        ]
    except Exception as e:
        logger.error(f"Unable to get installed software on {agent.salt_id}: {e}")
        return

    if not InstalledSoftware.objects.filter(agent=agent).exists():
        InstalledSoftware(agent=agent, software=software).save()
    else:
        s = agent.installedsoftware_set.get()
        s.software = software
        s.save(update_fields=["software"])

    return "ok"


@app.task
def install_program(pk, name, version):
    agent = Agent.objects.get(pk=pk)

    r = agent.salt_api_cmd(
        timeout=900,
        func="chocolatey.install",
        arg=[name, f"version={version}"],
    )

    if r == "timeout" or r == "error":
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

    get_installed_software.delay(agent.pk)

    return "ok"
