from tacticalrmm.celery import app
from agents.models import Agent
from .models import Script


@app.task
def run_script_bg_task(data):
    agent = Agent.objects.get(pk=data["agentpk"])
    script = Script.objects.get(pk=data["scriptpk"])

    agent.salt_api_async(
        func="win_agent.run_script",
        kwargs={
            "filepath": script.filepath,
            "filename": script.filename,
            "shell": script.shell,
            "timeout": data["timeout"],
            "args": data["args"],
        },
    )


@app.task
def run_bulk_script_task(data):
    # for powershell and batch scripts only, workaround for salt bg script bug
    script = Script.objects.get(pk=data["scriptpk"])

    Agent.salt_batch_async(
        minions=data["minions"],
        func="win_agent.run_script",
        kwargs={
            "filepath": script.filepath,
            "filename": script.filename,
            "shell": script.shell,
            "timeout": data["timeout"],
            "args": data["args"],
        },
    )
