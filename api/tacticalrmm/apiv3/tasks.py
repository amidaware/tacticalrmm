from tacticalrmm.celery import app
from django.shortcuts import get_object_or_404
import asyncio
from agents.models import Agent
import time

@app.task
def update_systray_config():
    agents = Agent.objects.all()
    for agent in agents:
        cmd = {"func": "systrayconfig"}
        # Assuming agent.nats_cmd is an async function. Adapt this as necessary.
        asyncio.run(agent.nats_cmd(cmd, wait=False))
    time.sleep(1)