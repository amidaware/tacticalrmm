def _is_su(request):
    return request.user.is_superuser
