import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SCRIPTS_DIR = "/opt/trmm-community-scripts"

DOCKER_BUILD = False

LOG_DIR = os.path.join(BASE_DIR, "tacticalrmm/private/log")

EXE_DIR = os.path.join(BASE_DIR, "tacticalrmm/private/exe")

LINUX_AGENT_SCRIPT = BASE_DIR / "core" / "agent_linux.sh"

AUTH_USER_MODEL = "accounts.User"

# latest release
TRMM_VERSION = "0.13.5-dev"

# https://github.com/amidaware/tacticalrmm-web
WEB_VERSION = "0.100.0-dev"

# bump this version everytime vue code is changed
# to alert user they need to manually refresh their browser
APP_VER = "0.0.164"

# https://github.com/amidaware/rmmagent
LATEST_AGENT_VER = "2.1.0-dev"

MESH_VER = "1.0.22"

NATS_SERVER_VER = "2.8.4"

# for the update script, bump when need to recreate venv
PIP_VER = "30"

SETUPTOOLS_VER = "59.6.0"
WHEEL_VER = "0.37.1"

# AGENT_BASE_URL = "https://agents.tacticalrmm.com"
AGENT_BASE_URL = "https://trmm-test.tacticalrmm.com"
CHECK_TOKEN_URL = f"{AGENT_BASE_URL}/api/v2/checktoken"
AGENTS_URL = f"{AGENT_BASE_URL}/api/v2/agents/?"
EXE_GEN_URL = f"{AGENT_BASE_URL}/api/v2/exe"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

ASGI_APPLICATION = "tacticalrmm.asgi.application"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False  # disabled for performance, enable when we add translation support
USE_TZ = True

STATIC_URL = "/static/"

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "tacticalrmm/static/")]

REST_KNOX = {
    "TOKEN_TTL": timedelta(hours=5),
    "AUTO_REFRESH": True,
    "MIN_REFRESH_INTERVAL": 600,
}

DEMO = False
DEBUG = False
ADMIN_ENABLED = False
HOSTED = False
REDIS_HOST = "127.0.0.1"

try:
    from .local_settings import *
except ImportError:
    pass

if "GHACTIONS" in os.environ:
    DEBUG = False
    ADMIN_ENABLED = False
    DEMO = False

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "knox.auth.TokenAuthentication",
        "tacticalrmm.auth.APIAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Tactical RMM API",
    "DESCRIPTION": "Simple and Fast remote monitoring and management tool",
    "VERSION": TRMM_VERSION,
    "AUTHENTICATION_WHITELIST": ["tacticalrmm.auth.APIAuthentication"],
}


if not DEBUG:
    REST_FRAMEWORK.update(
        {"DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",)}
    )

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "rest_framework.authtoken",
    "knox",
    "corsheaders",
    "accounts",
    "apiv3",
    "clients",
    "agents",
    "checks",
    "services",
    "winupdate",
    "software",
    "core",
    "automation",
    "autotasks",
    "logs",
    "scripts",
    "alerts",
    "drf_spectacular",
]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, 6379)],
        },
    },
}

# silence cache key length warnings
import warnings

from django.core.cache import CacheKeyWarning

warnings.simplefilter("ignore", CacheKeyWarning)

CACHES = {
    "default": {
        "BACKEND": "tacticalrmm.cache.TacticalRedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379",
        "OPTIONS": {
            "parser_class": "redis.connection.HiredisParser",
            "pool_class": "redis.BlockingConnectionPool",
            "db": "10",
        },
    }
}

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  ##
    "tacticalrmm.middleware.LogIPMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tacticalrmm.middleware.AuditMiddleware",
]

if DEBUG and not DEMO:
    INSTALLED_APPS += (
        "django_extensions",
        "silk",
    )

    MIDDLEWARE.insert(0, "silk.middleware.SilkyMiddleware")

if ADMIN_ENABLED:
    MIDDLEWARE += ("django.contrib.messages.middleware.MessageMiddleware",)
    INSTALLED_APPS += (
        "django.contrib.admin",
        "django.contrib.messages",
    )

if HOSTED:
    try:
        import trmm_mon
    except ImportError:
        pass
    else:
        INSTALLED_APPS += ("trmm_mon",)

if DEMO:
    MIDDLEWARE += ("tacticalrmm.middleware.DemoMiddleware",)


ROOT_URLCONF = "tacticalrmm.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "tacticalrmm.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
    },
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "django_debug.log"),
            "formatter": "verbose",
        }
    },
    "loggers": {
        "django.request": {"handlers": ["file"], "level": "ERROR", "propagate": True}
    },
}


if "GHACTIONS" in os.environ:
    print("-----------------------GHACTIONS----------------------------")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "pipeline",
            "USER": "pipeline",
            "PASSWORD": "pipeline123456",
            "HOST": "127.0.0.1",
            "PORT": "",
        }
    }
    SECRET_KEY = "abcdefghijklmnoptravis123456789"
    ALLOWED_HOSTS = ["api.example.com"]
    ADMIN_URL = "abc123456/"
    CORS_ORIGIN_WHITELIST = ["https://rmm.example.com"]
    MESH_USERNAME = "pipeline"
    MESH_SITE = "https://example.com"
    MESH_TOKEN_KEY = "bd65e957a1e70c622d32523f61508400d6cd0937001a7ac12042227eba0b9ed625233851a316d4f489f02994145f74537a331415d00047dbbf13d940f556806dffe7a8ce1de216dc49edbad0c1a7399c"
    REDIS_HOST = "localhost"
