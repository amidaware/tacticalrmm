from loguru import logger
from tacticalrmm.celery import app
from django.conf import settings

logger.configure(**settings.LOG_CONFIG)


@app.task
def cancel_pending_action_task(data):

    if data["action_type"] == "schedreboot" and data["status"] == "pending":

        from agents.models import Agent

        agent = Agent.objects.get(pk=data["agent"])

        task_name = data["details"]["taskname"]
        r = agent.salt_api_cmd(
            timeout=30, func="task.delete_task", arg=[f"name={task_name}"]
        )
        if r == "timeout" or r == "error" or (isinstance(r, bool) and not r):
            logger.error(
                f"Unable to contact {agent.hostname}. Task {task_name} will need to cancelled manually."
            )
            return
        else:
            logger.info(f"Scheduled reboot cancelled on {agent.hostname}")

    return "ok"
