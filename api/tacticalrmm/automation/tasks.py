from automation.models import Policy
from checks.models import Check
from tacticalrmm.celery import app


@app.task
def generate_agent_checks_from_policies_task(policypk, many=False):

    if many:
        policy_list = Policy.objects.filter(pk__in=policypk)
        for policy in policy_list:
            for agent in policy.related_agents():
                agent.generate_checks_from_policies()
    else:
        policy = Policy.objects.get(pk=policypk)
        for agent in policy.related_agents():
            agent.generate_checks_from_policies()

@app.task
def generate_agent_checks_task(agents):

    if agents:
        for agent in agents:
            agent.generate_checks_from_policies()

@app.task
def delete_policy_check_task(checkpk):

    Check.objects.filter(parent_check=checkpk).delete()

@app.task
def update_policy_check_fields_task(checkpk, fields, many=False):

    Check.objects.filter(parent_check=checkpk).update(**fields)