import os

ENVIRONMENT = os.getenv("DJANGO_ENV", "local").strip().lower()

if ENVIRONMENT in {"prod", "production"}:
    from .production import *  # noqa: F403
else:
    from .local import *  # noqa: F403
