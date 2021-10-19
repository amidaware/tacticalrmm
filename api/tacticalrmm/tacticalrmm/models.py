from django.db import models

class PermissionQuerySet(models.QuerySet):

    # filters queryset based on permissions. Works different for Agent, Client, and Site
    def filter_by_role(self, user):

        role = user.role
        can_view_clients = (
            role.can_view_clients.all().values_list("pk", flat=True) if role else None
        )
        can_view_sites = (
            role.can_view_sites.all().values_list("pk", flat=True) if role else None
        )

        clients_queryset = models.Q()
        sites_queryset = models.Q()
        policy_queryset = models.Q()
        model_name = self.model._meta.label.split(".")[1]

        # returns normal queryset if user is superuser
        if user.is_superuser or (role and getattr(role, "is_superuser")):
            return self

        # checks which sites and clients the user has access to and filters agents
        if model_name == "Agent":
            if can_view_clients:
                clients_queryset = models.Q(site__client_id__in=can_view_clients)

            if can_view_sites:
                sites_queryset = models.Q(site_id__in=can_view_sites)

            return self.filter(clients_queryset | sites_queryset)

        # checks which sites and clients the user has access to and filters clients and sites
        elif model_name == "Client" and can_view_clients:
            return self.filter(id__in=can_view_clients)
        elif model_name == "Site" and can_view_sites:
            return self.filter(id__in=can_view_sites)

        # anything else just checks the agent_id field and if it has it will filter matched agents from the queryset
        else:
            if not hasattr(self.model, "agent"):
                return self

            # if model that is being filtered is a Check or Automated task we need to allow checks/tasks that are associated with policies
            if model_name in ["Check", "AutomatedTask"] and (
                can_view_clients or can_view_sites
            ):
                policy_queryset = models.Q(agent=None)  # dont filter if agent is None

            if can_view_clients:
                clients_queryset = models.Q(agent__site__client_id__in=can_view_clients)
            if can_view_sites:
                sites_queryset = models.Q(agent__site_id__in=can_view_sites)

            return self.filter(
                clients_queryset | sites_queryset | policy_queryset
            )
