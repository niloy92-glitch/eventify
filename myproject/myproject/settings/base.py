from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

from .env import env_bool, env_first, env_int, env_str


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = env_str("DJANGO_SECRET_KEY", "django-insecure-dev-key")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = [host.strip() for host in env_str("ALLOWED_HOSTS", "*").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "myproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "myproject.wsgi.application"
ASGI_APPLICATION = "myproject.asgi.application"

USE_SQLITE = env_bool("USE_SQLITE", False)
DATABASE_URL = env_str("DATABASE_URL", "")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=env_int("POSTGRES_CONN_MAX_AGE", 600),
            ssl_require=env_str("POSTGRES_SSLMODE", "prefer") == "require",
        )
    }
elif USE_SQLITE:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env_first(["DB_NAME", "POSTGRES_DB"], "eventify_db"),
            "USER": env_first(["DB_USER", "POSTGRES_USER"], "postgres"),
            "PASSWORD": env_first(["DB_PASSWORD", "POSTGRES_PASSWORD"], ""),
            "HOST": env_first(["DB_HOST", "POSTGRES_HOST"], "127.0.0.1"),
            "PORT": int(env_first(["DB_PORT", "POSTGRES_PORT"], "5432")),
            "CONN_MAX_AGE": env_int("POSTGRES_CONN_MAX_AGE", 600),
            "OPTIONS": {"sslmode": env_str("POSTGRES_SSLMODE", "prefer")},
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.EventUser"

REQUIRE_EMAIL_VERIFICATION = env_bool("REQUIRE_EMAIL_VERIFICATION", True)

GOOGLE_OAUTH_CLIENT_ID = env_str("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = env_str("GOOGLE_OAUTH_CLIENT_SECRET", "")

EMAIL_BACKEND = env_str("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env_str("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = env_str("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env_str("EMAIL_HOST_PASSWORD", "")

EMAIL_BRAND_NAME = env_str("EMAIL_BRAND_NAME", "Eventify")
EMAIL_BRAND_PRIMARY = env_str("EMAIL_BRAND_PRIMARY", "#f97316")
EMAIL_BRAND_SECONDARY = env_str("EMAIL_BRAND_SECONDARY", "#10b981")
EMAIL_BRAND_BG = env_str("EMAIL_BRAND_BG", "#fff7ed")
EMAIL_BRAND_CARD = env_str("EMAIL_BRAND_CARD", "#ffffff")
EMAIL_BRAND_TEXT = env_str("EMAIL_BRAND_TEXT", "#1f2937")
EMAIL_BRAND_MUTED = env_str("EMAIL_BRAND_MUTED", "#6b7280")

SENDER_ADDRESS = env_str("SENDER_ADDRESS", EMAIL_HOST_USER or "no-reply@example.com")
SENDER_NAME = env_str("SENDER_NAME", EMAIL_BRAND_NAME)
DEFAULT_FROM_EMAIL = f"{SENDER_NAME} <{SENDER_ADDRESS}>"
