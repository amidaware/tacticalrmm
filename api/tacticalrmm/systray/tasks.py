from tacticalrmm.celery import app
import asyncio
from agents.models import Agent
import time


@app.task
def update_systray_config():
    agents = Agent.objects.all()
    for agent in agents:
        cmd = {"func": "systrayconfig"}
        asyncio.run(agent.nats_cmd(cmd, wait=False))
    time.sleep(1)
