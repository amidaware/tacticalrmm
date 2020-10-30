from loguru import logger

from django.conf import settings
from tacticalrmm.celery import app
from accounts.models import User
from agents.models import Agent

logger.configure(**settings.LOG_CONFIG)


@app.task
def core_maintenance_tasks():
    # cleanup any leftover agent user accounts
    agents = Agent.objects.values_list("agent_id", flat=True)
    users = User.objects.exclude(username__in=agents).filter(last_login=None)
    if users:
        users.delete()
        logger.info(
            "Removed leftover agent user accounts:", [i.username for i in users]
        )
