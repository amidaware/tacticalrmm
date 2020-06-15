from automation.models import Policy
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
def generate_policy_checks_from_agents_task(agents)

    if agents:
        for agent in agents:
            agent.generate_checks_from_policies()

@app.task
def update_policy_check_fields_task(policypk, **fields, many=False)

    if many:
        policy_list = Policy.objects.filter(pk__in=policypk)
        for policy in policy_list:
            for agent in policy.related_agents():
                agent.generate_checks_from_policies()
    else:
        policy = Policy.objects.get(pk=policypk)
        for agent in policy.related_agents():
            agent.generate_checks_from_policies()