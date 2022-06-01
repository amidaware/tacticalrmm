SECRET_KEY = "DJANGO_SEKRET"

DEBUG = False

ALLOWED_HOSTS = ['rmmdomain']

ADMIN_URL = "ADMINURL/"

CORS_ORIGIN_WHITELIST = [
    "https://frontenddomain"
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tacticalrmm',
        'USER': 'pgusername',
        'PASSWORD': 'pgpw',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

MESH_USERNAME = "meshusername"
MESH_SITE = "https://meshdomain"
REDIS_HOST    = "localhost"
ADMIN_ENABLED = True
