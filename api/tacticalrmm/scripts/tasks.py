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
