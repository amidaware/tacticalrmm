def _has_perm(request, perm):
    if request.user.is_superuser or (
        request.user.role and getattr(request.user.role, "is_superuser")
    ):
        return True

    return request.user.role and getattr(request.user.role, perm)
