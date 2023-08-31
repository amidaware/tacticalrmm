from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from accounts.models import User


class PermissionQuerySet(models.QuerySet):
    # filters queryset based on permissions. Works different for Agent, Client, and Site
    def filter_by_role(self, user: "User") -> "models.QuerySet":
        role = user.role

        # returns normal queryset if user is superuser
        if user.is_superuser or (role and getattr(role, "is_superuser")):
            return self

        can_view_clients = role.can_view_clients.all() if role else None
        can_view_sites = role.can_view_sites.all() if role else None

        clients_queryset = models.Q()
        sites_queryset = models.Q()
        agent_queryset = models.Q()
        model_name = self.model._meta.label.split(".")[1]

        # checks which sites and clients the user has access to and filters agents
        if model_name in ("Agent", "Deployment"):
            if can_view_clients:
                clients_queryset = models.Q(site__client__in=can_view_clients)

            if can_view_sites:
                sites_queryset = models.Q(site__in=can_view_sites)

            return self.filter(clients_queryset | sites_queryset)

        # checks which sites and clients the user has access to and filters clients and sites
        elif model_name == "Client" and (can_view_clients or can_view_sites):
            if can_view_sites:
                sites_queryset = models.Q(
                    pk__in=[site.client.pk for site in can_view_sites]
                )

            if can_view_clients:
                clients_queryset = models.Q(
                    pk__in=can_view_clients.values_list("pk", flat=True)
                )

            return self.filter(sites_queryset | clients_queryset)

        elif model_name == "Site" and (can_view_sites or can_view_clients):
            if can_view_clients:
                clients_queryset = models.Q(client__in=can_view_clients)
            if can_view_sites:
                sites_queryset = models.Q(
                    pk__in=can_view_sites.values_list("pk", flat=True)
                )

            return self.filter(clients_queryset | sites_queryset)

        elif model_name == "Alert":
            custom_alert_queryset = models.Q()
            if can_view_clients:
                clients_queryset = models.Q(agent__site__client__in=can_view_clients)
            if can_view_sites:
                sites_queryset = models.Q(agent__site__in=can_view_sites)
            if can_view_clients or can_view_sites:
                custom_alert_queryset = models.Q(
                    agent=None, assigned_check=None, assigned_task=None
                )

            return self.filter(
                clients_queryset | sites_queryset | custom_alert_queryset
            )

        # anything else just checks the agent field and if it has it will filter matched agents from the queryset
        else:
            if not hasattr(self.model, "agent"):
                return self

            # if model that is being filtered is a Check or Automated task we need to allow checks/tasks that are associated with policies
            if model_name in ("Check", "AutomatedTask", "DebugLog") and (
                can_view_clients or can_view_sites
            ):
                agent_queryset = models.Q(agent=None)  # dont filter if agent is None

            if can_view_clients:
                clients_queryset = models.Q(agent__site__client__in=can_view_clients)
            if can_view_sites:
                sites_queryset = models.Q(agent__site__in=can_view_sites)

            return self.filter(clients_queryset | sites_queryset | agent_queryset)
