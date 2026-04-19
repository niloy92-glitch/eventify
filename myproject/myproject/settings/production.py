from .base import *  # noqa: F403

from .env import env_bool, env_str, required_env

DEBUG = env_bool("DEBUG", False)
SECRET_KEY = required_env("DJANGO_SECRET_KEY")

ALLOWED_HOSTS = [host.strip() for host in env_str("ALLOWED_HOSTS", "").split(",") if host.strip()]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
