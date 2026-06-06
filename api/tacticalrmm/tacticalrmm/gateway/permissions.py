from tacticalrmm.permissions import _has_perm


class GatewayPerms:
    @staticmethod
    def user_can_use_terminal(user) -> bool:
        if user.is_superuser:
            return True
        if not user.role:
            return False
        if getattr(user.role, "is_superuser", False):
            return True
        return getattr(user.role, "can_use_terminal", False)
