from agents.models import Agent
from .models import WinUpdate

from djangormm.celery import app

@app.task
def check_for_updates_task(pk):

    agent = Agent.objects.get(pk=pk)

    resp = agent.salt_api_cmd(
        hostname=agent.hostname,
        timeout=310,
        salt_timeout=300,
        func="win_wua.list",
        arg="skip_installed=False"
    )
    data = resp.json()
    ret = data["return"][0][agent.hostname]

    guids = []
    for k in ret.keys():
        guids.append(k)

    if not WinUpdate.objects.filter(agent=agent).exists():

        for i in guids:
            WinUpdate(
                agent=agent,
                guid=i,
                kb=ret[i]["KBs"][0],
                mandatory=ret[i]["Mandatory"],
                title=ret[i]["Title"],
                needs_reboot=ret[i]["NeedsReboot"],
                installed=ret[i]["Installed"],
                downloaded=ret[i]["Downloaded"],
                description=ret[i]["Description"]
            ).save()
    else:
        for i in guids:
            # check if existing update install status has changed
            if WinUpdate.objects.filter(guid=i).exists():

                update = WinUpdate.objects.get(guid=i)

                if ret[i]["Installed"] != update.installed:
                    update.installed = not update.installed
                    update.save(update_fields=["installed"])

            # otherwise it's a new update
            else:
                WinUpdate(
                    agent=agent,
                    guid=i,
                    kb=ret[i]["KBs"][0],
                    mandatory=ret[i]["Mandatory"],
                    title=ret[i]["Title"],
                    needs_reboot=ret[i]["NeedsReboot"],
                    installed=ret[i]["Installed"],
                    downloaded=ret[i]["Downloaded"],
                    description=ret[i]["Description"]
                ).save()
    return "ok"