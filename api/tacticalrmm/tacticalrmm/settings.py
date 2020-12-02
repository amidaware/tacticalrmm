import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCRIPTS_DIR = "/srv/salt/scripts"

DOCKER_BUILD = False

LOG_DIR = os.path.join(BASE_DIR, "tacticalrmm/private/log")

EXE_DIR = os.path.join(BASE_DIR, "tacticalrmm/private/exe")

AUTH_USER_MODEL = "accounts.User"

# latest release
TRMM_VERSION = "0.2.4"

# bump this version everytime vue code is changed
# to alert user they need to manually refresh their browser
APP_VER = "0.0.94"

# https://github.com/wh1te909/salt
LATEST_SALT_VER = "1.1.0"

# https://github.com/wh1te909/rmmagent
LATEST_AGENT_VER = "1.1.1"

MESH_VER = "0.7.9"

SALT_MASTER_VER = "3002.2"

# for the update script, bump when need to recreate venv or npm install
PIP_VER = "3"
NPM_VER = "2"

DL_64 = f"https://github.com/wh1te909/rmmagent/releases/download/v{LATEST_AGENT_VER}/winagent-v{LATEST_AGENT_VER}.exe"
DL_32 = f"https://github.com/wh1te909/rmmagent/releases/download/v{LATEST_AGENT_VER}/winagent-v{LATEST_AGENT_VER}-x86.exe"

SALT_64 = f"https://github.com/wh1te909/salt/releases/download/{LATEST_SALT_VER}/salt-minion-setup.exe"
SALT_32 = f"https://github.com/wh1te909/salt/releases/download/{LATEST_SALT_VER}/salt-minion-setup-x86.exe"

try:
    from .local_settings import *
except ImportError:
    pass

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "knox",
    "corsheaders",
    "accounts",
    "apiv2",
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
]

if not "TRAVIS" in os.environ and not "AZPIPELINE" in os.environ:
    if DEBUG:
        INSTALLED_APPS += ("django_extensions",)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  ##
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tacticalrmm.middleware.AuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


REST_KNOX = {
    "TOKEN_TTL": timedelta(hours=5),
    "AUTO_REFRESH": True,
    "MIN_REFRESH_INTERVAL": 600,
}

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


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


STATIC_URL = "/static/"

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "tacticalrmm/static/")]


LOG_CONFIG = {
    "handlers": [{"sink": os.path.join(LOG_DIR, "debug.log"), "serialize": False}]
}

if "AZPIPELINE" in os.environ:
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

    REST_FRAMEWORK = {
        "DATETIME_FORMAT": "%b-%d-%Y - %H:%M",
        "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
        "DEFAULT_AUTHENTICATION_CLASSES": ("knox.auth.TokenAuthentication",),
        "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    }

    ALLOWED_HOSTS = ["api.example.com"]
    DOCKER_BUILD = True
    DEBUG = True
    SECRET_KEY = "abcdefghijklmnoptravis123456789"

    ADMIN_URL = "abc123456/"

    SCRIPTS_DIR = os.path.join(Path(BASE_DIR).parents[1], "scripts")
    SALT_USERNAME = "pipeline"
    SALT_PASSWORD = "pipeline"
    MESH_USERNAME = "pipeline"
    MESH_SITE = "https://example.com"
    MESH_TOKEN_KEY = "bd65e957a1e70c622d32523f61508400d6cd0937001a7ac12042227eba0b9ed625233851a316d4f489f02994145f74537a331415d00047dbbf13d940f556806dffe7a8ce1de216dc49edbad0c1a7399c"
    REDIS_HOST = "localhost"
    SALT_HOST = "127.0.0.1"
