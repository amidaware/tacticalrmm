from rest_framework.throttling import AnonRateThrottle


class CheckCredsMinThrottle(AnonRateThrottle):
    scope = "check_creds_min"


class CheckCredsDayThrottle(AnonRateThrottle):
    scope = "check_creds_day"


class LoginMinThrottle(AnonRateThrottle):
    scope = "login_min"


class LoginDayThrottle(AnonRateThrottle):
    scope = "login_day"
