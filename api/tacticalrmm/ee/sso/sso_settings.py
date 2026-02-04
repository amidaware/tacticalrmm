"""
Copyright (c) 2024-present Y12.AI Inc.
Y12.AI - Intelligent Remote Monitoring and Management
"""

HEADLESS_ONLY = True
SOCIALACCOUNT_ONLY = True
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_ADAPTER = "ee.sso.adapter.TacticalSocialAdapter"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_EMAIL_VERIFICATION = True

SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {"OAUTH_PKCE_ENABLED": True},
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "OAUTH_PKCE_ENABLED": True,
        "APP": {
            "client_id": "416218053988-7442gmek0v3hv74s6ts88gcf2kr6a8ar.apps.googleusercontent.com",
            "secret": "",  # Add your Google OAuth client secret here
            "key": "",
        },
    },
}

SESSION_COOKIE_SECURE = True
CORS_ALLOW_CREDENTIALS = True

# Y12.AI Domain Configuration
Y12_DOMAIN = "y12.ai"
