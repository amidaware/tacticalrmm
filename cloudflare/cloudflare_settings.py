"""
Y12.AI Cloudflare Containers Settings
Override settings for Cloudflare deployment with external services
"""

import os
import dj_database_url

# Database - Use Neon/Supabase PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,
        )
    }

# Redis/Cache - Use Upstash
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "ssl_cert_reqs": None,
            },
        },
    }
}

# Celery - Use Upstash Redis
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": "CERT_NONE"}
CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": "CERT_NONE"}

# Static/Media Files - Use Cloudflare R2
AWS_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "y12-assets")
AWS_S3_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
AWS_S3_REGION_NAME = "auto"
AWS_DEFAULT_ACL = None
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
AWS_QUERYSTRING_AUTH = False

if AWS_ACCESS_KEY_ID:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"

# Security Settings for Cloudflare
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cloudflare-specific headers
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Trust Cloudflare IPs
CLOUDFLARE_IPS = [
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22",
]

# CORS Settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://y12.ai",
    "https://www.y12.ai",
]

# Allowed Hosts
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "y12.ai,api.y12.ai,ws.y12.ai").split(",")

# CSRF Settings
CSRF_TRUSTED_ORIGINS = [
    "https://y12.ai",
    "https://api.y12.ai",
]

# Logging for Cloudflare
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "cloudflare": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "cloudflare",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

# MeshCentral - Disable if not using external MeshCentral
MESH_ENABLED = os.environ.get("MESH_ENABLED", "false").lower() == "true"
MESH_WS_URL = os.environ.get("MESH_WS_URL", "")
MESH_HOST = os.environ.get("MESH_HOST", "")

# Agent Settings
AGENT_BASE_URL = os.environ.get("AGENT_BASE_URL", "https://agents.y12.ai")

# Y12.AI Branding
APP_NAME = "Y12.AI"
APP_TAGLINE = "Intelligent Remote Monitoring and Management"
