import os
import sys
from contextlib import suppress
from datetime import timedelta
from pathlib import Path

from tacticalrmm.util_settings import get_backend_url, get_root_domain, get_webdomain

BASE_DIR = Path(__file__).resolve().parent.parent

SCRIPTS_DIR = "/opt/trmm-community-scripts"

DOCKER_BUILD = False

LOG_DIR = os.path.join(BASE_DIR, "tacticalrmm/private/log")

EXE_DIR = os.path.join(BASE_DIR, "tacticalrmm/private/exe")

LINUX_AGENT_SCRIPT = BASE_DIR / "core" / "agent_linux.sh"

MAC_UNINSTALL = BASE_DIR / "core" / "mac_uninstall.sh"

AUTH_USER_MODEL = "accounts.User"

# latest release
TRMM_VERSION = "0.20.2-dev"

# https://github.com/amidaware/tacticalrmm-web
WEB_VERSION = "0.101.52"

# bump this version everytime vue code is changed
# to alert user they need to manually refresh their browser
APP_VER = "0.0.197"

# https://github.com/amidaware/rmmagent
LATEST_AGENT_VER = "2.8.0"

MESH_VER = "1.1.32"

NATS_SERVER_VER = "2.10.22"

# Install Nushell on the agent
# https://github.com/nushell/nushell
INSTALL_NUSHELL = True
# GitHub version to download. The file will be downloaded from GitHub, extracted and installed.
# Version to download. If INSTALL_NUSHELL_URL is not provided, the file will be downloaded from GitHub,
# extracted and installed.
INSTALL_NUSHELL_VERSION = "0.93.0"
# URL to download directly. This is expected to be the direct URL, unauthenticated, uncompressed, ready to be installed.
# Use {OS}, {ARCH} and {VERSION} to specify the GOOS, GOARCH and INSTALL_NUSHELL_VERSION respectively.
# Windows: The ".exe" extension will be added automatically.
# Examples:
#   https://examplle.com/download/nushell/{OS}/{ARCH}/{VERSION}/nu
#   https://examplle.com/download/nushell/nu-{VERSION}-{OS}-{ARCH}
INSTALL_NUSHELL_URL = ""
# Enable Nushell config on the agent
# The default is to not enable the config because it could change how scripts run.
# However, disabling the config prevents plugins from being registered.
# https://github.com/nushell/nushell/issues/10754
# False: --no-config-file option is added to the command line.
# True: --config and --env-config options are added to the command line and point to the Agent's directory.
NUSHELL_ENABLE_CONFIG = False

# Install Deno on the agent
# https://github.com/denoland/deno
INSTALL_DENO = True
# Version to download. If INSTALL_DENO_URL is not provided, the file will be downloaded from GitHub,
# extracted and installed.
INSTALL_DENO_VERSION = "v1.44.4"
# URL to download directly. This is expected to be the direct URL, unauthenticated, uncompressed, ready to be installed.
# Use {OS}, {ARCH} and {VERSION} to specify the GOOS, GOARCH and INSTALL_DENO_VERSION respectively.
# Windows: The ".exe" extension will be added automatically.
# Examples:
#   https://examplle.com/download/deno/{OS}/{ARCH}/{VERSION}/deno
#   https://examplle.com/download/deno/deno-{VERSION}-{OS}-{ARCH}
INSTALL_DENO_URL = ""
# Default permissions for Deno
# Space separated list of permissions as listed in the documentation.
# https://docs.deno.com/runtime/manual/basics/permissions#permissions
# Examples:
#   DENO_DEFAULT_PERMISSIONS = "--allow-sys --allow-net --allow-env"
#   DENO_DEFAULT_PERMISSIONS = "--allow-all"
DENO_DEFAULT_PERMISSIONS = "--allow-all"

# for the update script, bump when need to recreate venv
PIP_VER = "45"

SETUPTOOLS_VER = "75.1.0"
WHEEL_VER = "0.44.0"

AGENT_BASE_URL = "https://agents.tacticalrmm.com"

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
SWAGGER_ENABLED = False
REDIS_HOST = "127.0.0.1"
TRMM_LOG_LEVEL = "ERROR"
TRMM_LOG_TO = "file"
TRMM_PROTO = "https"
TRMM_BACKEND_PORT = None

if not DOCKER_BUILD:
    ALLOWED_HOSTS = []
    CORS_ORIGIN_WHITELIST = []

with suppress(ImportError):
    from ee.sso.sso_settings import *  # noqa

with suppress(ImportError):
    from .local_settings import *  # noqa

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

if not DOCKER_BUILD:

    TRMM_ROOT_DOMAIN = get_root_domain(ALLOWED_HOSTS[0])
    frontend_domain = get_webdomain(CORS_ORIGIN_WHITELIST[0]).split(":")[0]

    ALLOWED_HOSTS.append(frontend_domain)

    if DEBUG:
        ALLOWED_HOSTS.append("*")

    backend_url = get_backend_url(ALLOWED_HOSTS[0], TRMM_PROTO, TRMM_BACKEND_PORT)

    SESSION_COOKIE_DOMAIN = TRMM_ROOT_DOMAIN
    CSRF_COOKIE_DOMAIN = TRMM_ROOT_DOMAIN
    CSRF_TRUSTED_ORIGINS = [CORS_ORIGIN_WHITELIST[0], backend_url]
    HEADLESS_FRONTEND_URLS = {
        "socialaccount_login_error": f"{CORS_ORIGIN_WHITELIST[0]}/account/provider/callback"
    }

CHECK_TOKEN_URL = f"{AGENT_BASE_URL}/api/v2/checktoken"
AGENTS_URL = f"{AGENT_BASE_URL}/api/v2/agents/?"
EXE_GEN_URL = f"{AGENT_BASE_URL}/api/v2/exe"
WEBTAR_DL_URL = f"{AGENT_BASE_URL}/api/v2/webtar/?"

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
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.openid_connect",
    "allauth.headless",
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
    "ee.reporting",
    "ee.sso",
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
import warnings  # noqa

from django.core.cache import CacheKeyWarning  # noqa

warnings.simplefilter("ignore", CacheKeyWarning)

CACHES = {
    "default": {
        "BACKEND": "tacticalrmm.cache.TacticalRedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379",
        "OPTIONS": {
            "parser_class": "redis.connection._HiredisParser",
            "pool_class": "redis.BlockingConnectionPool",
            "db": "10",
        },
    }
}

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "tacticalrmm.middleware.LogIPMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tacticalrmm.middleware.AuditMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "ee.sso.middleware.SSOIconMiddleware",
]

if SWAGGER_ENABLED:
    INSTALLED_APPS += ("drf_spectacular",)

if DEBUG and not DEMO:
    INSTALLED_APPS.insert(0, "daphne")
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


def get_log_level() -> str:
    if "TRMM_LOG_LEVEL" in os.environ:
        return os.getenv("TRMM_LOG_LEVEL")  # type: ignore

    return TRMM_LOG_LEVEL


def configure_logging_handler():
    cfg = {
        "level": get_log_level(),
        "formatter": "verbose",
    }

    log_to = os.getenv("TRMM_LOG_TO", TRMM_LOG_TO)

    if log_to == "stdout":
        cfg["class"] = "logging.StreamHandler"
        cfg["stream"] = sys.stdout
    else:
        cfg["class"] = "logging.FileHandler"
        cfg["filename"] = os.path.join(LOG_DIR, "trmm_debug.log")

    return cfg


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
    },
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "django_debug.log"),
            "formatter": "verbose",
        },
        "trmm": configure_logging_handler(),
    },
    "loggers": {
        "django.request": {"handlers": ["file"], "level": "ERROR", "propagate": True},
        "trmm": {"handlers": ["trmm"], "level": get_log_level(), "propagate": False},
    },
}
