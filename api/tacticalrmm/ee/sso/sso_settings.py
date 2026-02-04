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
    },
}

SESSION_COOKIE_SECURE = True
CORS_ALLOW_CREDENTIALS = True

# Google OAuth Settings (configure these in local_settings.py or environment variables)
# GOOGLE_CLIENT_ID = "your-google-client-id.apps.googleusercontent.com"
# GOOGLE_CLIENT_SECRET = "your-google-client-secret"
