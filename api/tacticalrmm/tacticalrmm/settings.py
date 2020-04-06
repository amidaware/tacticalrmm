import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUTH_USER_MODEL = 'accounts.User'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'knox',
    'corsheaders',
    'accounts',
    'api',
    'clients',
    'agents',
    'checks',
    'services',
    'winupdate',
    'software',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware', ##
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


REST_KNOX = {
  'TOKEN_TTL': timedelta(hours=5),
  'AUTO_REFRESH': True,
  'MIN_REFRESH_INTERVAL': 600
}

ROOT_URLCONF = 'tacticalrmm.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tacticalrmm.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'tacticalrmm/static/')
]


LOG_CONFIG = {
    "handlers": [
        {"sink": os.path.join(BASE_DIR, "log/debug.log"), "serialize": False}
    ]
}

try:
    from .local_settings import *
except ImportError:
    pass

if 'TRAVIS' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'travisci',
            'USER': 'travisci',
            'PASSWORD': 'travisSuperSekret6645',
            'HOST': '127.0.0.1',
            'PORT': ''
        }
    }

    REST_FRAMEWORK = {
        'DATETIME_FORMAT': "%b-%d-%Y - %H:%M",

        'DEFAULT_PERMISSION_CLASSES': (
            'rest_framework.permissions.IsAuthenticated',
        ),
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'knox.auth.TokenAuthentication',
        ),
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        )
    }

    DEBUG = True
    SECRET_KEY = 'abcdefghijklmnoptravis123456789'

    ADMIN_URL = "abc123456/"

    EMAIL_USE_TLS = True
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_HOST_USER = 'travis@example.com'
    EMAIL_HOST_PASSWORD = 'travis'
    EMAIL_PORT = 587
    EMAIL_ALERT_RECIPIENTS = ["travis@example.com",]

    SALT_USERNAME = "travis"
    SALT_PASSWORD = "travis"
    MESH_USERNAME = "travis"
    MESH_SITE = "https://example.com"
    REDIS_HOST = "localhost"
    SALT_HOST = "127.0.0.1"
    TWO_FACTOR_OTP = "TRAVIS"

if 'AZPIPELINE' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'pipeline',
            'USER': 'pipeline',
            'PASSWORD': 'pipeline123456',
            'HOST': '127.0.0.1',
            'PORT': ''
        }
    }

    REST_FRAMEWORK = {
        'DATETIME_FORMAT': "%b-%d-%Y - %H:%M",

        'DEFAULT_PERMISSION_CLASSES': (
            'rest_framework.permissions.IsAuthenticated',
        ),
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'knox.auth.TokenAuthentication',
        ),
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        )
    }

    DEBUG = True
    SECRET_KEY = 'abcdefghijklmnoptravis123456789'

    ADMIN_URL = "abc123456/"

    EMAIL_USE_TLS = True
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_HOST_USER = 'pipeline@example.com'
    EMAIL_HOST_PASSWORD = 'pipeline'
    EMAIL_PORT = 587
    EMAIL_ALERT_RECIPIENTS = ["pipeline@example.com",]

    SALT_USERNAME = "pipeline"
    SALT_PASSWORD = "pipeline"
    MESH_USERNAME = "pipeline"
    MESH_SITE = "https://example.com"
    REDIS_HOST = "localhost"
    SALT_HOST = "127.0.0.1"
    TWO_FACTOR_OTP = "ABC12345"