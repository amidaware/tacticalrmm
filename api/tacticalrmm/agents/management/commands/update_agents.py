from django.conf import settings
from django.core.management.base import BaseCommand
from packaging import version as pyver

from agents.models import Agent
from agents.tasks import send_agent_update_task
from core.utils import get_core_settings, token_is_valid
from tacticalrmm.constants import AGENT_DEFER


class Command(BaseCommand):
    help = "Triggers an agent update task to run"

    def handle(self, *args, **kwargs):
        core = get_core_settings()
        if not core.agent_auto_update:
            return

        q = Agent.objects.defer(*AGENT_DEFER).exclude(version=settings.LATEST_AGENT_VER)
        agent_ids: list[str] = [
            i.agent_id
            for i in q
            if pyver.parse(i.version) < pyver.parse(settings.LATEST_AGENT_VER)
        ]
        token, _ = token_is_valid()
        send_agent_update_task.delay(agent_ids=agent_ids, token=token, force=False)
