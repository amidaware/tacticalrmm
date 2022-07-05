SECRET_KEY = "DJANGO_SEKRET"

DEBUG = False

ALLOWED_HOSTS = ["api.example.com"]

ADMIN_URL = "ADMINURL/"

CORS_ORIGIN_WHITELIST = ["https://rmm.example.com"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "tacticalrmm",
        "USER": "pgusername",
        "PASSWORD": "pgpw",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

MESH_USERNAME = "meshusername"
MESH_SITE = "https://mesh.example.com"
REDIS_HOST = "localhost"
ADMIN_ENABLED = True
