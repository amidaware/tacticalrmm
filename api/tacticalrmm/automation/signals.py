from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from automation.models import Policy
from agents.models import Agent

def set_agent_policy_update_field(policy_list, many=False):

    if many:
        for policy in policy_list:
            policy.related_agents().update(policies_pending=True)
    else:
        policy_list.related_agents().update(policies_pending=True)

@receiver(post_save, sender="checks.Check")
def post_save_check_handler(sender, instance, created, **kwargs):

    # don't run when policy managed check is saved
    if instance.managed_by_policy == True:
        return

    # For created checks
    if created:
        if instance.policy != None:
            set_agent_policy_update_field(instance.policy)
        elif instance.agent != None:
            instance.agent.policies_pending=True
            instance.agent.save()

    # Checks that are updated except for agent
    else:
        if instance.policy != None:
            set_agent_policy_update_field(instance.policy)

@receiver(pre_delete, sender="checks.Check")
def post_delete_check_handler(sender, instance, **kwargs):

    # don't run when policy managed check is saved
    if instance.managed_by_policy == True:
        return

    if instance.policy != None:
        set_agent_policy_update_field(instance.policy)
    elif instance.agent != None:
        instance.agent.policies_pending=True
        instance.agent.save()

@receiver([post_save, pre_delete], sender="automation.Policy")
def post_save_policy_handler(sender, instance, **kwargs):  

    set_agent_policy_update_field(instance)
