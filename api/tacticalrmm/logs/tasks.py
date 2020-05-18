from loguru import logger
from tacticalrmm.celery import app
from django.conf import settings

from .models import PendingAction

logger.configure(**settings.LOG_CONFIG)


@app.task
def cancel_pending_action_task(data):

    if data["action_type"] == "schedreboot" and data["status"] == "pending":

        from agents.models import Agent

        task_name = data["details"]["taskname"]
        try:
            resp = Agent.salt_api_cmd(
                hostname=data["salt_id"],
                timeout=45,
                func="task.delete_task",
                arg=[f"name={task_name}"],
            )
        except Exception as e:
            logger.error(
                f"Unable to contact {data['salt_id']}. Task {task_name} will need to cancelled manually."
            )
        else:
            logger.info(f"Scheduled reboot cancellled: {resp.json()}")

    return "ok"
