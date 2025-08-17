"""
Copyright (c) 2024-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

HEADLESS_ONLY = True
SOCIALACCOUNT_ONLY = True
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_ADAPTER = "ee.sso.adapter.TacticalSocialAdapter"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_EMAIL_VERIFICATION = True

SOCIALACCOUNT_PROVIDERS = {"openid_connect": {"OAUTH_PKCE_ENABLED": True}}

SESSION_COOKIE_SECURE = True
CORS_ALLOW_CREDENTIALS = True
