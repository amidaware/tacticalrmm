from django.shortcuts import get_object_or_404


def _has_perm(request, perm):
    if request.user.is_superuser or (
        request.user.role and getattr(request.user.role, "is_superuser")
    ):
        return True
    
    # make sure non-superusers with empty roles aren't permitted
    elif not request.user.role:
        return False

    return request.user.role and getattr(request.user.role, perm)


def _has_perm_on_agent(user, agent_id):
    from agents.models import Agent

    role = user.role
    if user.is_superuser or (role and getattr(role, "is_superuser")):
        return True

    # make sure non-superusers with empty roles aren't permitted
    elif not role:
        return False

    agent = get_object_or_404(Agent, agent_id=agent_id)
    can_view_clients = role.can_view_clients.all() if role else None
    can_view_sites = role.can_view_sites.all() if role else None

    if not can_view_clients and not can_view_sites:
        return True

    elif can_view_clients and agent.client in can_view_clients:
        return True

    elif can_view_sites and agent.site in can_view_sites:
        return True
    else:
        return False

def _has_perm_on_client(user, client_id: int):
    from clients.models import Client
    role = user.role

    if user.is_superuser or (role and getattr(role, "is_superuser")):
        return True
    # make sure non-superusers with empty roles aren't permitted
    elif not role:
        return False

    client = get_object_or_404(Client, pk=client_id)
    can_view_clients = role.can_view_clients.all() if role else None

    if not can_view_clients:
        return True

    elif can_view_clients and client in can_view_clients:
        return True
    else:
        return False

def _has_perm_on_site(user, site_id: int):
    from clients.models import Site
    role = user.role
    if user.is_superuser or (role and getattr(role, "is_superuser")):
        return True

    # make sure non-superusers with empty roles aren't permitted
    elif not role:
        return False

    site = get_object_or_404(Site, pk=site_id)
    can_view_clients = role.can_view_clients.all() if role else None
    can_view_sites = role.can_view_sites.all() if role else None

    if not can_view_clients and not can_view_sites:
        return True

    elif can_view_sites and site in can_view_sites:
        return True

    elif can_view_clients and site.client in can_view_clients:
        return True

    else:
        return False
