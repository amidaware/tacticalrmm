from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from automation.models import Policy
from agents.models import Agent
from .tasks import generate_agent_checks_from_policies_task


@receiver(post_save, sender="checks.Check")
def post_save_check_handler(sender, instance, created, **kwargs):

    # don't run when policy managed check is saved
    if instance.managed_by_policy:
        return

    # For created checks
    if created:
        if instance.policy:
            generate_agent_checks_from_policies_task.delay(policypk=instance.pk)
        elif instance.agent:
            instance.agent.generate_checks_from_policies()

    # Checks that are updated except for agent
    else:
        if instance.policy:
            generate_agent_checks_from_policies_task.delay(policypk=instance.pk)


@receiver(pre_delete, sender="checks.Check")
def pre_delete_check_handler(sender, instance, **kwargs):

    # don't run when policy managed check is saved
    if instance.managed_by_policy:
        return

    # Policy check deleted
    if instance.policy:
        generate_agent_checks_from_policies_task.delay(policypk=instance.pk)

    # Agent check deleted
    elif instance.agent:
        instance.agent.generate_checks_from_policies()


@receiver([post_save, pre_delete], sender="automation.Policy")
def save_delete_policy_handler(sender, instance, **kwargs):

    # Generate agent checks on save and delete
    generate_agent_checks_from_policies_task.delay(policypk=instance.pk)
